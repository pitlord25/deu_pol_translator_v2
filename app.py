from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:dragontiger19990802@localhost/translator_db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['PROMPT_FILE'] = 'system_prompt.txt'
db = SQLAlchemy(app)
openAIClient = OpenAI()

class tbl_rules(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case = db.Column(db.String(1000), nullable=False)
    instruction = db.Column(db.String(2000), nullable=False)

# Define the Feedback model
class tbl_feedbacks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedback = db.Column(db.Text, nullable=False)
    
@app.route('/')
def home():
    return redirect(url_for('translate'))

@app.route('/translate', methods=['GET', 'POST'])
def translate():
    if request.method == 'POST':
        if 'add_feedback' in request.form:
            feedback_text = request.form['feedback']
            new_feedback = tbl_feedbacks(feedback=feedback_text)
            db.session.add(new_feedback)
            db.session.commit()
            flash('Feedback added successfully!', 'success')
            return redirect(url_for('translate'))

        if 'translate' in request.form:
            input_text = request.form['text_to_translate']

            # Retrieve rules from the database
            raw_rules = tbl_rules.query.all()
            rules_content = "Dodatkowe zasady, których należy przestrzegać:\n"
            for idx, rule in enumerate(raw_rules, 1):
                rules_content += f"Sprawa {idx}: {rule.case} -> {rule.instruction}\n"

            # Retrieve feedbacks from the database
            raw_feedbacks = tbl_feedbacks.query.all()
            feedbacks_content = "Noted Feedbacks:"
            for idx, feedback in enumerate(raw_feedbacks, 1):
                feedbacks_content += f"Sprawa {idx}: {feedback.feedback}\n"

            prompt_file = app.config['PROMPT_FILE']
            with open(prompt_file, 'r', encoding='utf-8') as file:
                prompt_text = file.read()

            # Prepare content for OpenAI API
            content = prompt_text + input_text + rules_content + feedbacks_content
            
            # Call OpenAI API
            response = openAIClient.chat.completions.create(
                model="gpt-4o",
                messages = [
                    {
                        "role" : "user",
                        "content" : content
                    }
                ]
            )
            translation = response.choices[0].message.content

            return render_template('translate.html', translation=translation)

    return render_template('translate.html')

@app.route('/rules', methods=['GET', 'POST'])
def rules():
    if request.method == 'POST':
        print(request.form)
        case = request.form['case']
        instruction = request.form['instruction']
        new_rule = tbl_rules(case=case, instruction=instruction)
        db.session.add(new_rule)
        db.session.commit()
        flash('Rule added successfully!', 'success')
        return redirect(url_for('rules'))
    all_rules = tbl_rules.query.all()
    return render_template('rules.html', rules=all_rules)

@app.route('/update_rule/<int:id>', methods=['POST'])
def update_rule(id):
    rule = tbl_rules.query.get_or_404(id)
    rule.case = request.form['rule_name']
    rule.instruction = request.form['rule_description']
    db.session.commit()
    flash('Rule updated successfully!', 'success')
    return redirect(url_for('rules'))

@app.route('/delete_rule/<int:id>')
def delete_rule(id):
    rule = tbl_rules.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    flash('Rule deleted successfully!', 'success')
    return redirect(url_for('rules'))

@app.route('/prompt', methods=['GET', 'POST'])
def prompt():
    prompt_file = app.config['PROMPT_FILE']
    
    if request.method == 'POST':
        prompt_text = request.form['prompt']
        prompt_text = prompt_text.rstrip('\n')
        with open(prompt_file, 'w', encoding='utf-8', newline='') as file:
            file.write(prompt_text)
        flash('Prompt updated successfully!', 'success')
        return redirect(url_for('prompt'))

    # Load the existing prompt from file
    if os.path.exists(prompt_file):
        with open(prompt_file, 'r', encoding='utf-8') as file:
            prompt_text = file.read()
    else:
        prompt_text = ''
    
    return render_template('prompt.html', prompt_text=prompt_text)

@app.route('/api/translate', methods=['POST'])
def api_translate():
    # Get the data from the request
    data = request.get_json()
    input_text = data.get('text_to_translate', '')

    # Retrieve rules from the database
    raw_rules = tbl_rules.query.all()
    rules_content = "Dodatkowe zasady, których należy przestrzegać:\n"
    for idx, rule in enumerate(raw_rules, 1):
        rules_content += f"Sprawa {idx}: {rule.case} -> {rule.instruction}\n"

    # Retrieve feedbacks from the database
    raw_feedbacks = tbl_feedbacks.query.all()
    feedbacks_content = "Noted Feedbacks:"
    for idx, feedback in enumerate(raw_feedbacks, 1):
        feedbacks_content += f"Sprawa {idx}: {feedback.feedback}\n"

    prompt_file = app.config['PROMPT_FILE']
    with open(prompt_file, 'r', encoding='utf-8') as file:
        prompt_text = file.read()

    # Prepare content for OpenAI API
    content = prompt_text + input_text + rules_content + feedbacks_content

    # Call OpenAI API
    response = openAIClient.chat.completions.create(
        model="gpt-4o",
        messages = [
            {
                "role" : "user",
                "content" : content
            }
        ]
    )
    translation = response.choices[0].message.content

    return jsonify({'translation': translation})

with app.app_context() :
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
