import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, abort, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import desc, func
from app import app, db
from models import User, Problem, TestCase, Submission, Contest, Announcement
from forms import *
from judge import judge_submission
import threading


@app.route('/')
def index():
    """Homepage with latest announcements and contest info"""
    announcements = Announcement.query.order_by(desc(Announcement.created_at)).limit(5).all()
    active_contest = Contest.query.filter_by(is_active=True).first()
    
    # Get some basic stats
    total_problems = Problem.query.filter_by(is_active=True).count()
    total_submissions = Submission.query.count()
    total_users = User.query.filter_by(is_active=True).count()
    
    return render_template('index.html', 
                         announcements=announcements,
                         active_contest=active_contest,
                         total_problems=total_problems,
                         total_submissions=total_submissions,
                         total_users=total_users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return redirect(url_for('login'))
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return render_template('register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            password_hash=generate_password_hash(form.password.data),
            role='contestant'
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Get user's recent submissions
    recent_submissions = Submission.query.filter_by(user_id=current_user.id)\
                                        .order_by(desc(Submission.submitted_at))\
                                        .limit(10).all()
    
    # Get user's solved problems count
    solved_problems = db.session.query(Problem.id).join(Submission)\
                               .filter(Submission.user_id == current_user.id,
                                     Submission.status == 'accepted')\
                               .distinct().count()
    
    # Get active contest
    active_contest = Contest.query.filter_by(is_active=True).first()
    
    return render_template('dashboard.html',
                         recent_submissions=recent_submissions,
                         solved_problems=solved_problems,
                         active_contest=active_contest)


@app.route('/problems')
def problems():
    """List all problems"""
    problems_list = Problem.query.filter_by(is_active=True).all()
    
    # Add solved status for logged-in users
    if current_user.is_authenticated:
        solved_problem_ids = set(
            row[0] for row in db.session.query(Problem.id).join(Submission)
            .filter(Submission.user_id == current_user.id,
                   Submission.status == 'accepted').all()
        )
        for problem in problems_list:
            problem.is_solved = problem.id in solved_problem_ids
    else:
        for problem in problems_list:
            problem.is_solved = False
    
    return render_template('problems.html', problems=problems_list)


@app.route('/problem/<int:problem_id>')
def problem_detail(problem_id):
    """Show problem details"""
    problem = Problem.query.get_or_404(problem_id)
    
    # Check if user has solved this problem
    is_solved = False
    if current_user.is_authenticated:
        solved_submission = Submission.query.filter_by(
            user_id=current_user.id,
            problem_id=problem_id,
            status='accepted'
        ).first()
        is_solved = solved_submission is not None
    
    return render_template('problem_detail.html', problem=problem, is_solved=is_solved)


@app.route('/problem/<int:problem_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_solution(problem_id):
    """Submit solution for a problem"""
    if not current_user.can_submit():
        flash('You do not have permission to submit solutions.', 'danger')
        return redirect(url_for('problems'))
    
    problem = Problem.query.get_or_404(problem_id)
    form = SubmissionForm()
    
    if form.validate_on_submit():
        submission = Submission(
            user_id=current_user.id,
            problem_id=problem_id,
            language=form.language.data,
            code=form.code.data,
            status='pending'
        )
        
        db.session.add(submission)
        db.session.commit()
        
        # Start judging in background
        thread = threading.Thread(target=judge_submission, args=(submission.id,))
        thread.daemon = True
        thread.start()
        
        flash('Solution submitted! Check the submissions page for results.', 'success')
        return redirect(url_for('submissions'))
    
    return render_template('submit.html', form=form, problem=problem)


@app.route('/submissions')
@login_required
def submissions():
    """Show user's submissions"""
    page = request.args.get('page', 1, type=int)
    user_submissions = Submission.query.filter_by(user_id=current_user.id)\
                                      .order_by(desc(Submission.submitted_at))\
                                      .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('submissions.html', submissions=user_submissions)


@app.route('/scoreboard')
def scoreboard():
    """Show contest scoreboard"""
    # Calculate scores per user
    query = db.session.query(
        User.id,
        User.username,
        User.full_name,
        func.count(Submission.id.distinct()).label('total_submissions'),
        func.count(
            db.case((Submission.status == 'accepted', 1), else_=None)
        ).label('solved_problems'),
        func.sum(
            db.case((Submission.status == 'accepted', Problem.points), else_=0)
        ).label('total_score')
    ).join(Submission, User.id == Submission.user_id, isouter=True)\
     .join(Problem, Submission.problem_id == Problem.id, isouter=True)\
     .filter(User.role.in_(['contestant', 'admin', 'judge']))\
     .group_by(User.id, User.username, User.full_name)\
     .order_by(desc('total_score'), 'total_submissions')
    
    scoreboard_data = query.all()
    
    return render_template('scoreboard.html', scoreboard=scoreboard_data)


@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    # Get user statistics
    total_submissions = Submission.query.filter_by(user_id=current_user.id).count()
    accepted_submissions = Submission.query.filter_by(user_id=current_user.id, status='accepted').count()
    
    # Get recent activity
    recent_submissions = Submission.query.filter_by(user_id=current_user.id)\
                                        .order_by(desc(Submission.submitted_at))\
                                        .limit(5).all()
    
    return render_template('profile.html',
                         total_submissions=total_submissions,
                         accepted_submissions=accepted_submissions,
                         recent_submissions=recent_submissions)


# Admin routes
@app.route('/admin')
@login_required
def admin():
    """Admin dashboard"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get statistics
    total_users = User.query.count()
    total_problems = Problem.query.count()
    total_submissions = Submission.query.count()
    pending_submissions = Submission.query.filter_by(status='pending').count()
    
    return render_template('admin.html',
                         total_users=total_users,
                         total_problems=total_problems,
                         total_submissions=total_submissions,
                         pending_submissions=pending_submissions)


@app.route('/admin/problems')
@login_required
def admin_problems():
    """Admin problem management"""
    if not current_user.is_judge():
        flash('Access denied. Judge privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    problems_list = Problem.query.all()
    return render_template('problems.html', problems=problems_list, admin_view=True)


@app.route('/admin/problem/create', methods=['GET', 'POST'])
@login_required
def create_problem():
    """Create new problem"""
    if not current_user.is_judge():
        flash('Access denied. Judge privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = ProblemForm()
    if form.validate_on_submit():
        # Check if problem code already exists
        existing = Problem.query.filter_by(code=form.code.data).first()
        if existing:
            flash('Problem code already exists.', 'danger')
            return render_template('create_problem.html', form=form)
        
        problem = Problem(
            title=form.title.data,
            code=form.code.data,
            statement=form.statement.data,
            input_format=form.input_format.data,
            output_format=form.output_format.data,
            constraints=form.constraints.data,
            sample_input=form.sample_input.data,
            sample_output=form.sample_output.data,
            time_limit=form.time_limit.data,
            memory_limit=form.memory_limit.data,
            difficulty=form.difficulty.data,
            points=form.points.data
        )
        
        db.session.add(problem)
        db.session.commit()
        
        flash('Problem created successfully!', 'success')
        return redirect(url_for('admin_problems'))
    
    return render_template('create_problem.html', form=form)


@app.route('/admin/problem/<int:problem_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_problem(problem_id):
    """Edit existing problem"""
    if not current_user.is_judge():
        flash('Access denied. Judge privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    problem = Problem.query.get_or_404(problem_id)
    form = ProblemForm(obj=problem)
    
    if form.validate_on_submit():
        # Check if problem code conflicts with another problem
        existing = Problem.query.filter(Problem.code == form.code.data, Problem.id != problem_id).first()
        if existing:
            flash('Problem code already exists.', 'danger')
            return render_template('edit_problem.html', form=form, problem=problem)
        
        form.populate_obj(problem)
        db.session.commit()
        
        flash('Problem updated successfully!', 'success')
        return redirect(url_for('admin_problems'))
    
    return render_template('edit_problem.html', form=form, problem=problem)


@app.route('/admin/problem/<int:problem_id>/test-cases')
@login_required
def manage_test_cases(problem_id):
    """Manage test cases for a problem"""
    if not current_user.is_judge():
        flash('Access denied. Judge privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    problem = Problem.query.get_or_404(problem_id)
    test_cases = TestCase.query.filter_by(problem_id=problem_id).all()
    
    return render_template('test_cases.html', problem=problem, test_cases=test_cases)


@app.route('/admin/problem/<int:problem_id>/add-test-case', methods=['GET', 'POST'])
@login_required
def add_test_case(problem_id):
    """Add test case to a problem"""
    if not current_user.is_judge():
        flash('Access denied. Judge privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    problem = Problem.query.get_or_404(problem_id)
    form = TestCaseForm()
    
    if form.validate_on_submit():
        test_case = TestCase(
            problem_id=problem_id,
            input_data=form.input_data.data,
            output_data=form.output_data.data,
            is_sample=form.is_sample.data,
            points=form.points.data
        )
        
        db.session.add(test_case)
        db.session.commit()
        
        flash('Test case added successfully!', 'success')
        return redirect(url_for('manage_test_cases', problem_id=problem_id))
    
    return render_template('add_test_case.html', form=form, problem=problem)


@app.route('/admin/submissions')
@login_required
def admin_submissions():
    """Admin view all submissions"""
    if not current_user.is_judge():
        flash('Access denied. Judge privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    all_submissions = Submission.query.order_by(desc(Submission.submitted_at))\
                                     .paginate(page=page, per_page=50, error_out=False)
    
    return render_template('submissions.html', submissions=all_submissions, admin_view=True)


@app.route('/admin/users')
@login_required
def admin_users():
    """Admin user management"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user details"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    form = EditUserForm(obj=user)
    
    if form.validate_on_submit():
        # Check username/email conflicts
        existing = User.query.filter(
            ((User.username == form.username.data) | (User.email == form.email.data)) &
            (User.id != user_id)
        ).first()
        
        if existing:
            flash('Username or email already exists.', 'danger')
            return render_template('edit_user.html', form=form, user=user)
        
        form.populate_obj(user)
        db.session.commit()
        
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('edit_user.html', form=form, user=user)


# API routes for real-time updates
@app.route('/api/submission/<int:submission_id>/status')
@login_required
def get_submission_status(submission_id):
    """Get submission status (AJAX)"""
    submission = Submission.query.get_or_404(submission_id)
    
    # Check if user owns this submission or is judge/admin
    if submission.user_id != current_user.id and not current_user.is_judge():
        abort(403)
    
    return jsonify({
        'status': submission.status,
        'score': submission.score,
        'execution_time': submission.execution_time,
        'memory_used': submission.memory_used,
        'judge_message': submission.judge_message
    })


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403
