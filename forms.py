from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, PasswordField, SelectField, IntegerField, DateTimeField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from wtforms.widgets import TextArea


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class ProblemForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    code = StringField('Problem Code', validators=[DataRequired(), Length(max=20)])
    statement = TextAreaField('statement', validators=[DataRequired()], widget=TextArea())
    input_format = TextAreaField('Input Format')
    output_format = TextAreaField('Output Format')
    constraints = TextAreaField('Constraints')
    sample_input = TextAreaField('Sample Input')
    sample_output = TextAreaField('Sample Output')
    time_limit = IntegerField('Time Limit (ms)', validators=[DataRequired(), NumberRange(min=100, max=10000)], default=1000)
    memory_limit = IntegerField('Memory Limit (MB)', validators=[DataRequired(), NumberRange(min=16, max=1024)], default=256)
    difficulty = SelectField('Difficulty', choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], default='easy')
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1, max=1000)], default=100)
    submit = SubmitField('Save Problem')


class TestCaseForm(FlaskForm):
    input_data = TextAreaField('Input Data', validators=[DataRequired()])
    output_data = TextAreaField('Expected Output', validators=[DataRequired()])
    is_sample = BooleanField('Is Sample Test Case')
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1, max=100)], default=10)
    submit = SubmitField('Add Test Case')


class SubmissionForm(FlaskForm):
    language = SelectField('Language', choices=[
        ('python3', 'Python 3'),
        ('cpp', 'C++'),
        ('c', 'C'),
        ('java', 'Java')
    ], validators=[DataRequired()])
    code = TextAreaField('Source Code', validators=[DataRequired()], render_kw={'rows': 20})
    submit = SubmitField('Submit Solution')


class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    is_important = BooleanField('Mark as Important')
    submit = SubmitField('Post Announcement')


class ContestForm(FlaskForm):
    name = StringField('Contest Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('description')
    start_time = DateTimeField('Start Time', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    end_time = DateTimeField('End Time', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    submit = SubmitField('Save Contest')


class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    role = SelectField('Role', choices=[
        ('visitor', 'Visitor'),
        ('contestant', 'Contestant'),
        ('judge', 'Judge'),
        ('admin', 'Administrator')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active')
    submit = SubmitField('Update User')
