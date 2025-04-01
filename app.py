import os
from flask import Flask, request, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///draft_game.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------------------------------------------------
#  ADMIN CHECK
# ------------------------------------------------------------------
def is_admin():
    return request.args.get("key") == "analytics"

# ------------------------------------------------------------------
#  DATABASE MODELS
# ------------------------------------------------------------------
class Entrant(db.Model):
    __tablename__ = 'entrants'
    entrant_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    team_name = db.Column(db.String(100), nullable=True)

class Prediction(db.Model):
    __tablename__ = 'predictions'
    prediction_id = db.Column(db.Integer, primary_key=True)
    entrant_id = db.Column(db.Integer, db.ForeignKey('entrants.entrant_id'))
    pick_number = db.Column(db.Integer)
    predicted_player_name = db.Column(db.String(100))
    points_awarded = db.Column(db.Integer, default=0)

class ActualPick(db.Model):
    __tablename__ = 'actual_picks'
    pick_number = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(100))

class EntrantStanding(db.Model):
    __tablename__ = 'entrant_standings'
    entrant_id = db.Column(db.Integer, db.ForeignKey('entrants.entrant_id'), primary_key=True)
    total_score = db.Column(db.Integer, default=0)

# ------------------------------------------------------------------
#  CONFIG
# ------------------------------------------------------------------
MAX_PICK_NUMBER = 32  # We allow picks 1..32
CHUNK_SIZE = 10       # Chunk the picks in sub-tables of this width

# If correct, user gets "pick_number" points (e.g., #5 => 5 points).
# We'll also ensure users must pick from the official list, and
# the admin's "pick number" is forced 1..32.

# This is the 200-player suggestion list (position, college in parentheses).
# The user must pick from these names or we show an error message.
PLAYER_NAME_SUGGESTIONS = [
    "Abdul Carter, LB (Penn State)",
    "Aeneas Peebles, DL (Duke)",
    "Ahmed Hassanein, OT (Texas A&M)",
    "Aireontae Ersery, OT (Minnesota)",
    "Ajani Cornelius, OT (Oregon)",
    "Alfred Collins, DL (Texas)",
    "Alijah Huzzie, DB (North Carolina)",
    "Andrew Mukuba, DB (Texas)",
    "Anthony Belton, OT (NC State)",
    "Antwaun Powell-Ryland, EDGE (Virginia Tech)",
    "Arian Smith, WR (Georgia)",
    "Armand Membou, OL (Missouri)",
    "Ashton Gillotte, EDGE (Louisville)",
    "Ashton Jeanty, RB (Boise State)",
    "Azareye'h Thomas, DB (Florida State)",
    "Barrett Carter, LB (Clemson)",
    "Barryn Sorrell, DL (Texas)",
    "Benjamin Morrison, CB (Notre Dame)",
    "Benjamin Yurosek, TE (Stanford)",
    "Billy Bowman Jr., DB (Oklahoma)",
    "Bradyn Swinson, EDGE (LSU)",
    "Brandon Crenshaw-Dickson, OL (San Diego State)",
    "Brashard Smith, WR (Miami)",
    "CJ West, DL (Kent State)",
    "Caleb Rogers, OL (Texas Tech)",
    "Cam Skattebo, RB (Arizona State)",
    "Cam Ward, QB (Miami)",
    "Cameron Williams, OL (Oregon)",
    "Carson Schwesinger, LB (Air Force)",
    "Chandler Martin, LB (Memphis)",
    "Charles Grant, DL (Michigan)",
    "Chase Lundt, DB (Air Force)",
    "Chris Paul Jr., OL (Tulsa)",
    "Cobee Bryant, CB (Kansas)",
    "Colston Loveland, TE (Michigan)",
    "DJ Giddens, RB (Kansas State)",
    "Damien Martinez, RB (Miami)",
    "Dante Trader, S (Maryland)",
    "Darien Porter, WR (Iowa State)",
    "Darius Alexander, DL (Missouri State)",
    "David Walker, DL (Central Arkansas)",
    "Davison Igbinosun, CB (Ohio State)",
    "Demetrius Knight Jr., LB (Charlotte)",
    "Deone Walker, DL (Kentucky)",
    "Derrick Harmon, DL (Michigan State)",
    "Devin Neal, RB (Kansas)",
    "Dillon Gabriel, QB (Oregon)",
    "Donovan Ezeiruaku, EDGE (Boston College)",
    "Donovan Jackson, OL (Ohio State)",
    "Dorian Strong, CB (Virginia Tech)",
    "Drew Kendall, OL (Boston College)",
    "Dylan Fairchild, OL (Georgia)",
    "Dylan Sampson, RB (Tennessee)",
    "D’Eryk Jackson, LB (Kentucky)",
    "Elic Ayomanor, WR (Stanford)",
    "Elijah Arroyo, TE (Miami)",
    "Elijah Roberts, DL (SMU)",
    "Emeka Egbuka, WR (Ohio State)",
    "Emery Jones, OL (LSU)",
    "Garrett Nussmeier, QB (LSU)",
    "Grey Zabel, OL (North Dakota State)",
    "Gunnar Helm, TE (Texas)",
    "Harold Fannin Jr., TE (Bowling Green)",
    "Harold Perkins Jr., LB (LSU)",
    "Isaiah Bond, WR (Alabama)",
    "JJ Pegues, DL (Ole Miss)",
    "JT Tuimoloau, EDGE (Ohio State)",
    "Jack Bech, WR (TCU)",
    "Jack Kiser, LB (Notre Dame)",
    "Jack Sawyer, EDGE (Ohio State)",
    "Jacob Parrish, CB (Kansas State)",
    "Jacory Croskey-Merritt, RB (New Mexico)",
    "Jahdae Barron, DB (Texas)",
    "Jake Briningstool, TE (Clemson)",
    "Jalen Milroe, QB (Alabama)",
    "Jalen Rivers, OL (Miami)",
    "Jalen Royals, WR (Utah State)",
    "Jalen Travis, OL (Princeton)",
    "Jalon Walker, LB (Georgia)",
    "Jamaree Caldwell, DL (Houston)",
    "James Pearce Jr., EDGE (Tennessee)",
    "Jamon Dumas-Johnson, LB (Kentucky)",
    "Jared Ivey, EDGE (Ole Miss)",
    "Jared Wilson, OL (North Carolina)",
    "Jarquez Hunter, RB (Auburn)",
    "Javontez Spraggins, OL (Tennessee)",
    "Jaxson Dart, QB (Ole Miss)",
    "Jayden Higgins, WR (Iowa State)",
    "Jaydon Blue, RB (Texas)",
    "Jaylin Noel, WR (Iowa State)",
    "Jaylin Smith, LB (USC)",
    "Jeffrey Bassa, LB (Oregon)",
    "Jihaad Campbell, LB (Alabama)",
    "Jonah Savaiinaea, OL (Arizona)",
    "Jonas Sanker, DB (Virginia)",
    "Jordan Burch, DL (Oregon)",
    "Jordan Phillips, DL (Arizona)",
    "Josaiah Stewart, EDGE (Michigan)",
    "Josh Conerly Jr., OL (Oregon)",
    "Josh Simmons, OL (Ohio State)",
    "Joshua Farmer, DL (Florida State)",
    "Justin Walley, CB (Minnesota)",
    "Kaimon Rucker, EDGE (North Carolina)",
    "Kaleb Johnson, RB (Iowa)",
    "Kalel Mullings, LB (Michigan)",
    "Kelvin Banks Jr., OT (Texas)",
    "Kenneth Grant, DL (Michigan)",
    "Kevin Winston Jr., DB (Penn State)",
    "Kobe Hudson, WR (UCF)",
    "Kyle Kennard, EDGE (Georgia Tech)",
    "Kyle McCord, QB (Syracuse)",
    "Kyle Williams, WR (Washington State)",
    "Landon Jackson, DL (Arkansas)",
    "Lathan Ransom, S (Ohio State)",
    "Luke Kandra, OL (Cincinnati)",
    "Luther Burden III, WR (Missouri)",
    "Malaki Starks, S (Georgia)",
    "Marcus Mbow, OL (Purdue)",
    "Mason Graham, DL (Michigan)",
    "Mason Taylor, TE (LSU)",
    "Matthew Golden, WR (Texas)",
    "Maxwell Hairston, CB (Kentucky)",
    "Mello Dotson, CB (Kansas)",
    "Mike Green, DL (James Madison)",
    "Mitchell Evans, TE (Notre Dame)",
    "Mykel Williams, DL (Georgia)",
    "Nic Scourton, EDGE (Texas A&M)",
    "Nick Emmanwori, S (South Carolina)",
    "Nohl Williams, CB (Cal)",
    "Ollie Gordon ll, RB (Oklahoma State)",
    "Oluwafemi Oladejo, LB (UCLA)",
    "Omarion Hampton, RB (North Carolina)",
    "Omarr Norman-Lott, DL (Michigan State)",
    "Ozzy Trapilo, OL (Boston College)",
    "Pat Bryant, WR (Illinois)",
    "Princely Umanmielen, EDGE (Ole Miss)",
    "Quandarrius Robinson, EDGE (Alabama)",
    "Quincy Riley, CB (Louisville)",
    "Quinn Ewers, QB (Texas)",
    "Quinshon Judkins, RB (Ohio State)",
    "RJ Harvey, RB (UCF)",
    "Riley Leonard, QB (Notre Dame)",
    "Rylie Mills, DL (Notre Dame)",
    "Sai'vion Jones, DL (LSU)",
    "Savion Williams, WR (TCU)",
    "Sebastian Castro, DB (Iowa)",
    "Shavon Revel, CB (Coastal Carolina)",
    "Shedeur Sanders, QB (Colorado)",
    "Shemar Stewart, DL (Texas A&M)",
    "Shemar Turner, DL (Texas A&M)",
    "Simeon Barrow Jr., DL (Miami)",
    "T.J. Sanders, DL (South Carolina)",
    "Tahveon Nicholson, CB (Illinois)",
    "Tate Ratledge, OL (Georgia)",
    "Terrance Ferguson, TE (Oregon)",
    "Tetairoa McMillan, WR (Arizona)",
    "Tez Johnson, WR (Oregon)",
    "Tommi Hill, DB (Nebraska)",
    "Tory Horton, WR (Colorado State)",
    "Travis Hunter, WR/CB (Colorado)",
    "Tre Harris, WR (Ole Miss)",
    "TreVeyon Henderson, RB (Ohio State)",
    "Trevor Etienne, RB (Georgia)",
    "Trey Amos, CB (Alabama)",
    "Tyleik Williams, DL (Ohio State)",
    "Tyler Baron, EDGE (Ole Miss)",
    "Tyler Batty, DL (BYU)",
    "Tyler Booker, OL (Alabama)",
    "Tyler Warren, TE (Penn State)",
    "Walter Nolen, DL (Ole Miss)",
    "Will Campbell, OL (LSU)",
    "Will Howard, QB (Ohio State)",
    "Will Johnson, CB (Michigan)",
    "Willie Lampkin, OL (North Carolina)",
    "Wyatt Milum, OT (West Virginia)",
    "Xavier Restrepo, WR (Miami)",
    "Xavier Truss, OL (Georgia)",
    "Xavier Watts, S (Notre Dame)",
    "Zy Alexander, CB (LSU)"
]

STANDINGS_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cavs Draft Confidence Pool 🏈</title>
    <!-- Google Font (Poppins) for a modern look -->
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #b2d8b2 0%, #81c784 100%);
        }
        .navbar {
            background-color: #444;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 999;
        }
        .navbar a {
            color: #fff;
            text-decoration: none;
            margin-right: 20px;
            font-weight: 600;
        }
        .navbar a:hover {
            text-decoration: underline;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        h1 {
            margin: 20px 0;
            color: #3e2723;
            font-family: 'Poppins', sans-serif;
        }

        .scoreboard-title {
            text-align: center;
            margin-bottom: 10px;
            color: #4e342e;
            font-weight: 600;
        }
        .scoreboard-table {
            margin: 0 auto 30px auto;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            background-color: #6d4c41;
            color: #fff;
            width: 400px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .scoreboard-table th,
        .scoreboard-table td {
            padding: 10px;
            text-align: center;
            border: 1px solid #fff;
        }
        .scoreboard-table th {
            background-color: #5d4037;
        }

        .standings-section {
            margin-bottom: 40px;
        }
        .section-title {
            font-size: 1.2em;
            margin-bottom: 10px;
            text-decoration: underline;
            color: #4e342e;
            font-weight: 600;
        }

        .picks-table {
            width: 100%;
            border-collapse: collapse;
            border-radius: 6px;
            overflow: hidden;
            background: #fff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .picks-table th,
        .picks-table td {
            border: 1px solid #ddd;
            padding: 8px 10px;
            text-align: center;
        }
        .picks-table th {
            background-color: #f2f2f2;
            font-weight: 600;
        }

        .correct {
            background-color: #d4edda;
            color: #155724;
            font-weight: 600;
        }
        .incorrect {
            background-color: #f8d7da;
            color: #721c24;
            font-weight: 600;
        }
        .pending-cell {
            background-color: #fef9e7;
            color: #555;
        }
        .actual-pick {
            font-size: 0.9em;
            color: #6c757d;
        }
        .no-entrants {
            text-align: center;
            font-style: italic;
            color: #333;
        }
        .no-picks {
            color: #333;
            text-align: center;
            margin-bottom: 40px;
        }
    </style>
</head>
<body>
    <div class="navbar">
    <a href="{{ url_for('enter_picks') }}">Enter Your Picks</a>
    {% if is_admin() %}
        <a href="{{ url_for('admin_panel') }}">Admin Panel</a>
        <a href="{{ url_for('team_select') }}">Edit Team Predictions</a>
    {% endif %}
</div>

    <div class="container">
        <h1>Cavs Draft Confidence Pool 🏈</h1>

        {% if entrants_sorted|length > 0 %}
            <div class="scoreboard-title">Current Scoreboard (High to Low)</div>
            <table class="scoreboard-table">
                <thead>
                    <tr>
                        <th>Entrant (Team)</th>
                        <th>Total Score</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in entrants_sorted %}
                    <tr>
                        <td>{{ row.Entrant.name }}{% if row.Entrant.team_name %} ({{ row.Entrant.team_name }}){% endif %}</td>
                        <td>{{ row.total_score }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p class="no-entrants">No entrants found yet.</p>
        {% endif %}

        {% if all_picks|length == 0 %}
            <p class="no-picks">No actual picks have been recorded by the Admin yet.</p>
        {% else %}
            {% for chunk in chunked_picks %}
            <div class="standings-section">
                <div class="section-title">
                    Picks {{ chunk[0].pick_number }} to {{ chunk[-1].pick_number }}
                </div>
                <table class="picks-table">
                    <thead>
                        <tr>
                            <th>Entrant (Team)</th>
                            {% for pick in chunk %}
                            <th>
                                Pick #{{ pick.pick_number }}<br>
                                {% if pick.player_name %}
                                    <span class="actual-pick">{{ pick.player_name }}</span>
                                {% else %}
                                    <span class="actual-pick">Pending</span>
                                {% endif %}
                            </th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in entrants_sorted %}
                        <tr>
                            <td>{{ row.Entrant.name }}{% if row.Entrant.team_name %} ({{ row.Entrant.team_name }}){% endif %}</td>
                            {% for pick in chunk %}
                                {% set predicted = predictions[row.Entrant.entrant_id].get(pick.pick_number) 
                                   if row.Entrant.entrant_id in predictions else None %}
                                {% if pick.player_name %}
                                    {% if predicted and predicted == pick.player_name %}
                                        <td class="correct">✓</td>
                                    {% elif predicted %}
                                        <td class="incorrect">✗</td>
                                    {% else %}
                                        <td>-</td>
                                    {% endif %}
                                {% else %}
                                    {% if predicted %}
                                        <td class="pending-cell">
                                            {{ predicted }}
                                            <span style="font-size: 0.8em; color: #999;">
                                                (Pending)
                                            </span>
                                        </td>
                                    {% else %}
                                        <td>-</td>
                                    {% endif %}
                                {% endif %}
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endfor %}
        {% endif %}
    </div>
</body>
</html>
"""

ADMIN_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Draft Admin</title>
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        body {
            margin: 0;
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
        }
        .navbar {
            background-color: #444;
            padding: 10px 20px;
            position: sticky;
            top: 0;
            z-index: 999;
        }
        .navbar a {
            color: #fff;
            text-decoration: none;
            margin-right: 20px;
            font-weight: 600;
        }
        .navbar a:hover {
            text-decoration: underline;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            margin-top: 20px;
            color: #333;
        }
        .pick-form {
            margin: 5px 0 20px 0;
        }
        label {
            font-weight: 600;
            margin-right: 5px;
        }
        /* Force pick # to 1..32 */
        input[type="number"] {
            padding: 6px;
            width: 80px;
            margin-right: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        input[type="text"] {
            padding: 6px;
            width: 220px;
            margin-right: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        input[type="submit"] {
            padding: 6px 16px;
            background-color: #28a745;
            border: none;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
        }
        input[type="submit"]:hover {
            background-color: #218838;
        }
        .pick-table, .team-table {
            border-collapse: collapse;
            width: 60%;
            background: #fff;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .pick-table th, .pick-table td,
        .team-table th, .team-table td {
            border: 1px solid #ddd;
            padding: 8px 10px;
            text-align: center;
        }
        .pick-table th,
        .team-table th {
            background-color: #f2f2f2;
            font-weight: 600;
        }
        .delete-btn {
            background-color: #dc3545;
            padding: 6px 12px;
            border: none;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
        }
        .delete-btn:hover {
            background-color: #c82333;
        }
        .section-title {
            font-size: 1.2em;
            margin-top: 40px;
            margin-bottom: 10px;
            text-decoration: underline;
            color: #333;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="navbar">
    <a href="{{ url_for('standings') }}">View Standings</a>
    {% if is_admin() %}
        <a href="{{ url_for('enter_picks') }}">Enter Your Picks</a>
        <a href="{{ url_for('team_select') }}">Edit Team Predictions</a>
    {% endif %}
</div>

    <div class="container">
        <h1>Admin Panel</h1>
        <p>Use the form below to add or edit actual picks in real time.</p>

        <datalist id="player_list">
            {% for p_name in player_names %}
                <option value="{{ p_name }}">
            {% endfor %}
        </datalist>

        <form action="{{ url_for('update_pick') }}" method="POST" class="pick-form">
            <label for="pick_number">Pick #:</label>
            <input type="number" id="pick_number" name="pick_number" min="1" max="32" required>
            <label for="player_name">Player Name:</label>
            <input type="text" id="player_name" name="player_name" list="player_list" required>
            <input type="submit" value="Save New/Overwrite">
        </form>

        <h2>Edit Existing Picks</h2>
        <table class="pick-table">
            <tr>
                <th>Pick #</th>
                <th>Player Name</th>
                <th>Action</th>
            </tr>
            {% for pick in picks %}
            <tr>
                <td>{{ pick.pick_number }}</td>
                <td>
                    <form action="{{ url_for('update_pick') }}" method="POST" style="display:inline;">
                        <input type="hidden" name="pick_number" value="{{ pick.pick_number }}">
                        <input type="text" name="player_name" value="{{ pick.player_name }}" list="player_list">
                </td>
                <td>
                        <input type="submit" value="Save">
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>

        <div class="section-title">Delete a Team</div>
        <p>Click "Delete" to remove an entire team's entry (entrant + predictions + standings).</p>
        <table class="team-table">
            <tr>
                <th>Team Name</th>
                <th>Entrant Name</th>
                <th>Action</th>
            </tr>
            {% for row in teams_data %}
            <tr>
                <td>{{ row.team_name }}</td>
                <td>{{ row.name }}</td>
                <td>
                    <form action="{{ url_for('delete_team') }}" method="POST">
                        <input type="hidden" name="team_name" value="{{ row.team_name }}">
                        <input type="hidden" name="entrant_id" value="{{ row.entrant_id }}">
                        <button class="delete-btn" type="submit">Delete</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

ENTER_PICKS_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Enter Picks</title>
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        body {
            margin: 0;
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
        }
        .navbar {
            background-color: #444;
            padding: 10px 20px;
            position: sticky;
            top: 0;
            z-index: 999;
        }
        .navbar a {
            color: #fff;
            text-decoration: none;
            margin-right: 20px;
            font-weight: 600;
        }
        .navbar a:hover {
            text-decoration: underline;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            margin-top: 20px;
            color: #333;
        }
        label {
            font-weight: 600;
        }
        input[type="text"] {
            padding: 6px;
            width: 220px;
            margin: 5px 0;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        .pick-group {
            margin-bottom: 12px;
        }
        .submit-btn {
            padding: 8px 16px;
            background-color: #007BFF;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
        }
        .submit-btn:hover {
            background-color: #0056b3;
        }
        .datalist-instruction {
            font-size: 0.9em;
            color: #555;
            margin: 10px 0;
        }
        .error {
            color: red;
            font-weight: 600;
            margin: 10px 0;
        }
        .duplicate {
            border: 2px solid red;
        }
        datalist {
            display: none;
        }
    </style>
</head>
<body>
    <div class="navbar">
    <a href="{{ url_for('standings') }}">View Standings</a>
    {% if is_admin() %}
        <a href="{{ url_for('admin_panel') }}">Admin Panel</a>
        <a href="{{ url_for('team_select') }}">Edit Team Predictions</a>
    {% endif %}
</div>

    <div class="container">
        <h1>Enter Your Picks (Up to Pick #{{ max_pick }})</h1>
        {% if error_message %}
            <div class="error">{{ error_message }}</div>
        {% endif %}

        <p>
           Fill in your name, your team name (optional),
           and pick a player from the official suggestions for each pick.
        </p>
        <form method="POST" action="{{ url_for('submit_picks') }}">
            <label for="entrant_name">Your Name:</label><br>
            <input type="text" id="entrant_name" name="entrant_name" value="{{ form_data.entrant_name }}" required><br><br>

            <label for="team_name">Team Name (optional):</label><br>
            <input type="text" id="team_name" name="team_name" value="{{ form_data.team_name }}"><br><br>

            <datalist id="player_list">
                {% for p_name in player_names %}
                    <option value="{{ p_name }}">
                {% endfor %}
            </datalist>
            <div class="datalist-instruction">
                (Suggestions will appear when you begin typing a player name. 
                 We'll reject any custom name not in this list.)
            </div>
            <br>

            {% for pick_number in range(1, max_pick+1) %}
                {% set field_name = 'pick_' ~ pick_number %}
                {% set val = form_data.picks[field_name] if field_name in form_data.picks else '' %}
                <div class="pick-group">
                    <label>Pick #{{ pick_number }}:</label><br>
                    <input type="text"
                           name="pick_{{ pick_number }}"
                           placeholder="Player Name"
                           list="player_list"
                           value="{{ val }}"
                           class="{% if pick_number in duplicate_picks %}duplicate{% endif %}">
                </div>
            {% endfor %}

            <button class="submit-btn" type="submit">Submit Picks</button>
        </form>
    </div>
</body>
</html>
"""

TEAM_SELECT_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Select Team to Edit</title>
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        body {
            margin: 0;
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
        }
        .navbar {
            background-color: #444;
            padding: 10px 20px;
            position: sticky;
            top: 0;
            z-index: 999;
        }
        .navbar a {
            color: #fff;
            text-decoration: none;
            margin-right: 20px;
            font-weight: 600;
        }
        .navbar a:hover {
            text-decoration: underline;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            margin-top: 20px;
            color: #333;
        }
        .team-list {
            background: #fff;
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: 10px;
            width: 300px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .team-link {
            display: block;
            margin: 5px 0;
            color: #007BFF;
            text-decoration: none;
            font-weight: 600;
        }
        .team-link:hover {
            text-decoration: underline;
        }
        .no-teams {
            font-style: italic;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="navbar">
    <a href="{{ url_for('standings') }}">View Standings</a>
    {% if is_admin() %}
        <a href="{{ url_for('admin_panel') }}">Admin Panel</a>
        <a href="{{ url_for('enter_picks') }}">Enter Your Picks</a>
    {% endif %}
</div>
    <div class="container">
        <h1>Select a Team to View/Edit</h1>

        {% if teams %}
        <div class="team-list">
            {% for team in teams %}
                <a class="team-link" href="{{ url_for('edit_team', team_name=team) }}">{{ team }}</a>
            {% endfor %}
        </div>
        {% else %}
        <p class="no-teams">No teams found. (No one has entered a team name yet.)</p>
        {% endif %}
    </div>
</body>
</html>
"""

EDIT_TEAM_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Edit Team Predictions</title>
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        body {
            margin: 0;
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
        }
        .navbar {
            background-color: #444;
            padding: 10px 20px;
            position: sticky;
            top: 0;
            z-index: 999;
        }
        .navbar a {
            color: #fff;
            text-decoration: none;
            margin-right: 20px;
            font-weight: 600;
        }
        .navbar a:hover {
            text-decoration: underline;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            margin-top: 20px;
            color: #333;
        }
        .pick-group {
            margin-bottom: 12px;
        }
        .submit-btn {
            padding: 8px 16px;
            background-color: #007BFF;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
        }
        .submit-btn:hover {
            background-color: #0056b3;
        }
        input[type="text"] {
            padding: 6px;
            width: 220px;
            margin: 5px 0;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        .datalist-instruction {
            font-size: 0.9em;
            color: #555;
            margin: 10px 0;
        }
        .error {
            color: red;
            font-weight: 600;
            margin: 10px 0;
        }
        .duplicate {
            border: 2px solid red;
        }
        datalist {
            display: none;
        }
    </style>
</head>
<body>
    <div class="navbar">
    <a href="{{ url_for('team_select') }}">Select Another Team</a>
    <a href="{{ url_for('standings') }}">View Standings</a>
    {% if is_admin() %}
        <a href="{{ url_for('admin_panel') }}">Admin Panel</a>
        <a href="{{ url_for('enter_picks') }}">Enter New Picks</a>
    {% endif %}
</div>
    <div class="container">
        <h1>Edit Predictions for Team: {{ team_name }}</h1>
        
        {% if error_message %}
            <div class="error">{{ error_message }}</div>
        {% endif %}

        {% if entrant %}
            <form method="POST" action="{{ url_for('save_team', team_name=team_name) }}">
                <datalist id="player_list">
                    {% for p_name in player_names %}
                        <option value="{{ p_name }}">
                    {% endfor %}
                </datalist>
                <div class="datalist-instruction">
                    (Suggestions will appear when you begin typing a player name.
                     We only accept names from the list.)
                </div>
                <br>

                {% for pick_number in range(1, max_pick+1) %}
                    {% set val = form_data['pick_' ~ pick_number] if ('pick_' ~ pick_number) in form_data else '' %}
                    <div class="pick-group">
                        <label>Pick #{{ pick_number }}:</label><br>
                        <input type="text"
                            name="pick_{{ pick_number }}"
                            value="{{ val }}"
                            list="player_list"
                            class="{% if pick_number in duplicate_picks %}duplicate{% endif %}">
                    </div>
                {% endfor %}
                <button class="submit-btn" type="submit">Save Updates</button>
            </form>
        {% else %}
            <p>No entrant found for this team name.</p>
        {% endif %}
    </div>
</body>
</html>
"""

# ------------------------------------------------------------------
#  SCORING & HELPER FUNCTIONS
# ------------------------------------------------------------------

def recalc_scores_for_pick(pick_number, actual_player):
    """If correct, user gets pick_number points."""
    predictions = Prediction.query.filter_by(pick_number=pick_number).all()
    for p in predictions:
        p.points_awarded = pick_number if p.predicted_player_name == actual_player else 0
        db.session.add(p)
    db.session.commit()

    # Update total scores
    entrants = Entrant.query.all()
    for e in entrants:
        total_points = db.session.query(func.sum(Prediction.points_awarded))\
                                 .filter_by(entrant_id=e.entrant_id).scalar() or 0
        standing = EntrantStanding.query.filter_by(entrant_id=e.entrant_id).first()
        if not standing:
            standing = EntrantStanding(entrant_id=e.entrant_id, total_score=total_points)
            db.session.add(standing)
        else:
            standing.total_score = total_points
            db.session.add(standing)
    db.session.commit()

def recalc_all_picks():
    """Recompute scores for all actual picks in the DB."""
    all_actual_picks = ActualPick.query.all()
    for pick in all_actual_picks:
        recalc_scores_for_pick(pick.pick_number, pick.player_name)

def chunk_list(lst, chunk_size):
    """Split a list into sub-lists of length chunk_size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def find_duplicate_pick_numbers(pick_map):
    used = {}
    duplicates = set()
    for pnum, player in pick_map.items():
        if player:
            if player not in used:
                used[player] = [pnum]
            else:
                used[player].append(pnum)
    for player, picks in used.items():
        if len(picks) > 1:
            duplicates.update(picks)
    return duplicates

# ------------------------------------------------------------------
#  FLASK ROUTES
# ------------------------------------------------------------------

@app.route('/')
def standings():
    try:
        all_picks = ActualPick.query.order_by(ActualPick.pick_number).all()
    except Exception as e:
        all_picks = []
        print(f"Warning: actual_picks table not available yet. {e}")

    try:
        entrants_with_scores = (
            db.session.query(Entrant, EntrantStanding.total_score)
            .outerjoin(EntrantStanding, EntrantStanding.entrant_id == Entrant.entrant_id)
            .order_by(desc(EntrantStanding.total_score))
            .all()
        )
    except Exception as e:
        entrants_with_scores = []
        print(f"Warning: standings query failed. {e}")

    try:
        all_preds = Prediction.query.all()
    except Exception as e:
        all_preds = []
        print(f"Warning: predictions query failed. {e}")

    chunked_picks = list(chunk_list(all_picks, CHUNK_SIZE)) if all_picks else []

    predictions_dict = {}
    for pr in all_preds:
        if pr.entrant_id not in predictions_dict:
            predictions_dict[pr.entrant_id] = {}
        predictions_dict[pr.entrant_id][pr.pick_number] = pr.predicted_player_name

    return render_template_string(
        STANDINGS_HTML,
        all_picks=all_picks,
        chunked_picks=chunked_picks,
        entrants_sorted=entrants_with_scores,
        predictions=predictions_dict,
        is_admin=is_admin()
    )

@app.route('/admin')
def admin_panel():
    if not is_admin():
        return redirect(url_for('standings'))
    if request.args.get("key") != "analytics":
        return redirect(url_for('standings'))

    picks = ActualPick.query.order_by(ActualPick.pick_number).all()
    teams_data = db.session.query(Entrant).filter(Entrant.team_name.isnot(None)).all()
    return render_template_string(
        ADMIN_HTML,
        picks=picks,
        player_names=PLAYER_NAME_SUGGESTIONS,
        teams_data=teams_data,
        is_admin=is_admin()
    )

@app.route('/update_pick', methods=['POST'])
def update_pick():
    pick_number = request.form.get('pick_number', '')
    player_name = request.form.get('player_name', '').strip()

    # Force pick_number in [1..32].
    if not pick_number.isdigit():
        return redirect(url_for('admin_panel'))
    pick_num = int(pick_number)
    if pick_num < 1 or pick_num > 32:
        return redirect(url_for('admin_panel'))

    if not player_name:
        return redirect(url_for('admin_panel'))

    # ✅ ENFORCE official player list
    if player_name not in PLAYER_NAME_SUGGESTIONS:
        return redirect(url_for('admin_panel'))

    actual_pick = ActualPick.query.filter_by(pick_number=pick_num).first()
    if not actual_pick:
        actual_pick = ActualPick(pick_number=pick_num, player_name=player_name)
        db.session.add(actual_pick)
    else:
        actual_pick.player_name = player_name
    db.session.commit()

    recalc_scores_for_pick(pick_num, player_name)
    return redirect(url_for('admin_panel'))

@app.route('/delete_team', methods=['POST'])
def delete_team():
    team_name = request.form.get('team_name')
    entrant_id = request.form.get('entrant_id')
    if not team_name or not entrant_id:
        return redirect(url_for('admin_panel'))

    entrant = Entrant.query.filter_by(entrant_id=entrant_id).first()
    if entrant:
        Prediction.query.filter_by(entrant_id=entrant.entrant_id).delete()
        EntrantStanding.query.filter_by(entrant_id=entrant.entrant_id).delete()
        db.session.delete(entrant)
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/enter_picks')
def enter_picks():
    error_message = request.args.get('error', '')
    form_data = {"entrant_name": "", "team_name": "", "picks": {}}
    duplicate_picks = []
    return render_template_string(
        ENTER_PICKS_HTML,
        max_pick=MAX_PICK_NUMBER,
        player_names=PLAYER_NAME_SUGGESTIONS,
        error_message=error_message,
        form_data=form_data,
        duplicate_picks=duplicate_picks,
        is_admin=is_admin()
    )

@app.route('/submit_picks', methods=['POST'])
def submit_picks():
    entrant_name = request.form.get('entrant_name', '').strip()
    team_name = request.form.get('team_name', '').strip()
    pick_map = {}
    for pick_number in range(1, MAX_PICK_NUMBER + 1):
        val = request.form.get(f'pick_{pick_number}', '').strip()
        pick_map[pick_number] = val

    # Check duplicates
    duplicate_set = find_duplicate_pick_numbers(pick_map)
    if duplicate_set:
        error_message = "Duplicate picks detected! Please ensure each player is unique."
        form_data = {"entrant_name": entrant_name, "team_name": team_name, "picks": {}}
        for pick_number in range(1, MAX_PICK_NUMBER + 1):
            form_data["picks"][f'pick_{pick_number}'] = pick_map[pick_number]
        return render_template_string(
            ENTER_PICKS_HTML,
            max_pick=MAX_PICK_NUMBER,
            player_names=PLAYER_NAME_SUGGESTIONS,
            error_message=error_message,
            form_data=form_data,
            duplicate_picks=duplicate_set,
            is_admin=is_admin()
        )

    # Must ensure each picked name is in the official list
    for pn, player in pick_map.items():
        if player and (player not in PLAYER_NAME_SUGGESTIONS):
            error = f"'{player}' is not in the official suggestions. Please select only from the list."
            form_data = {"entrant_name": entrant_name, "team_name": team_name, "picks": {}}
            for pick_number in range(1, MAX_PICK_NUMBER + 1):
                form_data["picks"][f'pick_{pick_number}'] = pick_map[pick_number]
            return render_template_string(
                ENTER_PICKS_HTML,
                max_pick=MAX_PICK_NUMBER,
                player_names=PLAYER_NAME_SUGGESTIONS,
                error_message=error,
                form_data=form_data,
                duplicate_picks=[],
                is_admin=is_admin()
            )

    if not entrant_name:
        return redirect(url_for('enter_picks'))

    # Find or create entrant
    entrant = Entrant.query.filter_by(name=entrant_name).first()
    if not entrant:
        entrant = Entrant(name=entrant_name, team_name=team_name)
        db.session.add(entrant)
        db.session.commit()
    else:
        if team_name:
            entrant.team_name = team_name
        db.session.commit()

    # Save picks
    for pick_number in range(1, MAX_PICK_NUMBER + 1):
        predicted_player = pick_map[pick_number]
        if predicted_player:
            pred = Prediction.query.filter_by(entrant_id=entrant.entrant_id, pick_number=pick_number).first()
            if not pred:
                pred = Prediction(
                    entrant_id=entrant.entrant_id,
                    pick_number=pick_number,
                    predicted_player_name=predicted_player
                )
                db.session.add(pred)
            else:
                pred.predicted_player_name = predicted_player
    db.session.commit()

    recalc_all_picks()
    return redirect(url_for('standings'))

@app.route('/team_select')
def team_select():
    if not is_admin():
        return redirect(url_for('standings'))
    if request.args.get("key") != "analytics":
        return redirect(url_for('standings'))

    teams = db.session.query(Entrant.team_name)\
                      .filter(Entrant.team_name.isnot(None), Entrant.team_name != "")\
                      .distinct().all()
    team_list = [t[0] for t in teams]
    return render_template_string(
        TEAM_SELECT_HTML, 
        teams=team_list, 
        is_admin=is_admin()
    )

@app.route('/edit_team/<team_name>')
def edit_team(team_name):
    if not is_admin():
        return redirect(url_for('standings'))
    error_message = request.args.get('error', '')
    entrant = Entrant.query.filter_by(team_name=team_name).first()
    if not entrant:
        return render_template_string(
            EDIT_TEAM_HTML,
            team_name=team_name,
            entrant=None,
            form_data={},
            duplicate_picks=[],
            max_pick=MAX_PICK_NUMBER,
            player_names=PLAYER_NAME_SUGGESTIONS,
            error_message=error_message,
            is_admin=is_admin()
        )

    preds = Prediction.query.filter_by(entrant_id=entrant.entrant_id).all()
    form_data = {}
    for p in preds:
        field_name = f'pick_{p.pick_number}'
        form_data[field_name] = p.predicted_player_name

    duplicates_str = request.args.get('duplicates', '')
    duplicate_picks = set(int(x) for x in duplicates_str.split(',')) if duplicates_str else set()

    return render_template_string(
        EDIT_TEAM_HTML,
        team_name=team_name,
        entrant=entrant,
        form_data=form_data,
        duplicate_picks=duplicate_picks,
        max_pick=MAX_PICK_NUMBER,
        player_names=PLAYER_NAME_SUGGESTIONS,
        error_message=error_message,
        is_admin=is_admin()
    )

@app.route('/initdb')
def initdb():
    if not is_admin():
        return redirect(url_for('standings'))
    db.create_all()
    return "Database tables created!" 

@app.route('/save_team/<team_name>', methods=['POST'])
def save_team(team_name):
    entrant = Entrant.query.filter_by(team_name=team_name).first()
    if not entrant:
        return redirect(url_for('team_select'))

    pick_map = {}
    for pick_number in range(1, MAX_PICK_NUMBER + 1):
        val = request.form.get(f'pick_{pick_number}', '').strip()
        pick_map[pick_number] = val

    # Check duplicates
    duplicate_set = find_duplicate_pick_numbers(pick_map)
    if duplicate_set:
        error_message = "Duplicate picks detected! Please ensure each player is unique."
        form_data = {}
        for pn in range(1, MAX_PICK_NUMBER + 1):
            form_data[f'pick_{pn}'] = pick_map[pn]
        duplicates_str = ",".join(str(x) for x in duplicate_set)
        return redirect(url_for('edit_team',
                                team_name=team_name,
                                error=error_message,
                                duplicates=duplicates_str))

    # Also ensure picks are in the official list
    for pn, player in pick_map.items():
        if player and (player not in PLAYER_NAME_SUGGESTIONS):
            error = f"'{player}' is not in the official suggestions. Please select only from the list."
            form_data = {}
            for pick_number in range(1, MAX_PICK_NUMBER + 1):
                form_data[f'pick_{pick_number}'] = pick_map[pick_number]
            duplicates_str = ""
            return redirect(url_for('edit_team',
                                    team_name=team_name,
                                    error=error,
                                    duplicates=duplicates_str))

    # Save
    for pick_number in range(1, MAX_PICK_NUMBER + 1):
        predicted_player = pick_map[pick_number]
        pred = Prediction.query.filter_by(entrant_id=entrant.entrant_id, pick_number=pick_number).first()
        if predicted_player:
            if not pred:
                pred = Prediction(entrant_id=entrant.entrant_id,
                                  pick_number=pick_number,
                                  predicted_player_name=predicted_player)
                db.session.add(pred)
            else:
                pred.predicted_player_name = predicted_player
        else:
            if pred:
                pred.predicted_player_name = ""
        db.session.commit()

    recalc_all_picks()
    return redirect(url_for('standings'))

# ------------------------------------------------------------------
#  MAIN
# ------------------------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists('draft_game.db'):
            db.create_all()
            # No pre-populated data (start empty).
        else:
            db.create_all()

    app.run(host='0.0.0.0', port=10000)

