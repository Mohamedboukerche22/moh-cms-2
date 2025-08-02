import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from app import app, db
from models import Submission, TestCase


def judge_submission(submission_id):
    """Judge a submission against test cases"""
    with app.app_context():
        submission = Submission.query.get(submission_id)
        if not submission:
            return
        
        # Update status to judging
        submission.status = 'judging'
        db.session.commit()
        
        try:
            # Get test cases
            test_cases = TestCase.query.filter_by(problem_id=submission.problem_id).all()
            if not test_cases:
                submission.status = 'accepted'  # No test cases, auto-accept
                submission.score = submission.problem.points
                submission.judged_at = datetime.utcnow()
                db.session.commit()
                return
            
            total_score = 0
            max_time = 0
            max_memory = 0
            
            # Compile if needed
            if submission.language in ['cpp', 'c', 'java']:
                compile_result = compile_code(submission)
                if not compile_result['success']:
                    submission.status = 'compile_error'
                    submission.judge_message = compile_result['message']
                    submission.judged_at = datetime.utcnow()
                    db.session.commit()
                    return
            
            # Run against test cases
            for test_case in test_cases:
                result = run_test_case(submission, test_case)
                
                if result['status'] == 'accepted':
                    total_score += test_case.points
                elif result['status'] in ['time_limit', 'memory_limit', 'runtime_error']:
                    submission.status = result['status']
                    submission.judge_message = result.get('message', '')
                    break
                else:  # wrong_answer
                    if submission.status != 'wrong_answer':
                        submission.status = 'wrong_answer'
                
                max_time = max(max_time, result.get('time', 0))
                max_memory = max(max_memory, result.get('memory', 0))
            
            # Set final status
            if submission.status == 'judging':
                if total_score == sum(tc.points for tc in test_cases):
                    submission.status = 'accepted'
                else:
                    submission.status = 'wrong_answer'
            
            submission.score = total_score
            submission.execution_time = max_time
            submission.memory_used = max_memory
            submission.judged_at = datetime.utcnow()
            
        except Exception as e:
            app.logger.error(f"Error judging submission {submission_id}: {e}")
            submission.status = 'runtime_error'
            submission.judge_message = 'Internal judging error'
            submission.judged_at = datetime.utcnow()
        
        db.session.commit()


def compile_code(submission):
    """Compile code if necessary"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            if submission.language == 'cpp':
                source_file = os.path.join(temp_dir, 'solution.cpp')
                executable = os.path.join(temp_dir, 'solution')
                
                with open(source_file, 'w') as f:
                    f.write(submission.code)
                
                result = subprocess.run(
                    ['g++', '-o', executable, source_file, '-std=c++17'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return {'success': False, 'message': result.stderr}
                
            elif submission.language == 'c':
                source_file = os.path.join(temp_dir, 'solution.c')
                executable = os.path.join(temp_dir, 'solution')
                
                with open(source_file, 'w') as f:
                    f.write(submission.code)
                
                result = subprocess.run(
                    ['gcc', '-o', executable, source_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return {'success': False, 'message': result.stderr}
                
            elif submission.language == 'java':
                source_file = os.path.join(temp_dir, 'Solution.java')
                
                with open(source_file, 'w') as f:
                    f.write(submission.code)
                
                result = subprocess.run(
                    ['javac', source_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return {'success': False, 'message': result.stderr}
        
        return {'success': True}
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Compilation timeout'}
    except Exception as e:
        return {'success': False, 'message': f'Compilation error: {str(e)}'}


def run_test_case(submission, test_case):
    """Run submission against a single test case"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, 'input.txt')
            output_file = os.path.join(temp_dir, 'output.txt')
            
            # Write input
            with open(input_file, 'w') as f:
                f.write(test_case.input_data)
            
            # Prepare execution command
            if submission.language == 'python3':
                source_file = os.path.join(temp_dir, 'solution.py')
                with open(source_file, 'w') as f:
                    f.write(submission.code)
                cmd = ['python3', source_file]
                
            elif submission.language == 'cpp':
                source_file = os.path.join(temp_dir, 'solution.cpp')
                executable = os.path.join(temp_dir, 'solution')
                
                with open(source_file, 'w') as f:
                    f.write(submission.code)
                
                # Compile
                compile_result = subprocess.run(
                    ['g++', '-o', executable, source_file, '-std=c++17'],
                    capture_output=True,
                    timeout=30
                )
                if compile_result.returncode != 0:
                    return {'status': 'compile_error', 'message': compile_result.stderr}
                
                cmd = [executable]
                
            elif submission.language == 'c':
                source_file = os.path.join(temp_dir, 'solution.c')
                executable = os.path.join(temp_dir, 'solution')
                
                with open(source_file, 'w') as f:
                    f.write(submission.code)
                
                # Compile
                compile_result = subprocess.run(
                    ['gcc', '-o', executable, source_file],
                    capture_output=True,
                    timeout=30
                )
                if compile_result.returncode != 0:
                    return {'status': 'compile_error', 'message': compile_result.stderr}
                
                cmd = [executable]
                
            elif submission.language == 'java':
                source_file = os.path.join(temp_dir, 'Solution.java')
                
                with open(source_file, 'w') as f:
                    f.write(submission.code)
                
                # Compile
                compile_result = subprocess.run(
                    ['javac', source_file],
                    capture_output=True,
                    timeout=30
                )
                if compile_result.returncode != 0:
                    return {'status': 'compile_error', 'message': compile_result.stderr}
                
                cmd = ['java', '-cp', temp_dir, 'Solution']
            
            # Execute with time and memory limits
            start_time = time.time()
            
            try:
                with open(input_file, 'r') as stdin_file:
                    with open(output_file, 'w') as stdout_file:
                        process = subprocess.run(
                            cmd,
                            stdin=stdin_file,
                            stdout=stdout_file,
                            stderr=subprocess.PIPE,
                            timeout=submission.problem.time_limit / 1000.0,  # Convert ms to seconds
                            text=True
                        )
                
                execution_time = int((time.time() - start_time) * 1000)  # Convert to ms
                
                if process.returncode != 0:
                    return {
                        'status': 'runtime_error',
                        'message': process.stderr,
                        'time': execution_time
                    }
                
                # Read output
                with open(output_file, 'r') as f:
                    actual_output = f.read().strip()
                
                expected_output = test_case.output_data.strip()
                
                if actual_output == expected_output:
                    return {
                        'status': 'accepted',
                        'time': execution_time,
                        'memory': 0  # Memory measurement not implemented
                    }
                else:
                    return {
                        'status': 'wrong_answer',
                        'time': execution_time,
                        'message': f'Expected: {expected_output}\nGot: {actual_output}'
                    }
                    
            except subprocess.TimeoutExpired:
                return {'status': 'time_limit', 'time': submission.problem.time_limit}
                
    except Exception as e:
        app.logger.error(f"Error running test case: {e}")
        return {'status': 'runtime_error', 'message': str(e)}
