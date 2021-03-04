import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from math import ceil
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


# Checking User Function
def actual_user(username):
    if "user" in session.keys():
        if session["user"] == username:
            return True

    return False


@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/get_recipes/")
def get_recipes():
    recipes = list(mongo.db.recipes.find())

    return render_template("recipes.html", recipes=recipes)


@app.route('/search_recipes/<query>', methods=['GET', 'POST'])
def search_recipes(query):

    # search Recipes function
    if search:
        recipes = list(
            mongo.db.recipes.find({"category_name": query}))

    return render_template("recipes.html", recipes=recipes)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    return render_template("recipes.html", recipes=recipes)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check for username presence in DB
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "email": request.form.get("email").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "user_img": request.form.get("user_img")
        }
        mongo.db.users.insert_one(register)

        # Let the user in their session
        session["user"] = request.form.get("username").lower()
        flash("Welcome, Food Lover!")
        return redirect(url_for("profile", username=session["user"]))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # checking Username presence in DB
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # Stored hashed password must match user's input
            if check_password_hash(
                existing_user["password"], request.form.get(
                    "password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(request.form.get("username")))
                return redirect(url_for(
                        "profile", username=session["user"]))
            else:
                # if the passwords don't match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # Username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # Display Username in session using DB data
    user = mongo.db.users.find_one(
        {"username": session["user"]})

    if not actual_user(username.lower()):
        return redirect(url_for("login"))

    if "user" in session.keys():
        if session["user"] == username:
            recipes = list(
                mongo.db.recipes.find({"created_by": username.lower()}))

        # page number fetching
        page = int(request.args.get('page') or 1)
        num = 2

        # count instances for pagination
        count = ceil(float(len(recipes) / num))

        # page -1 to check if the first items are found
        start = (page - 1) * num
        finish = start + num
        show_recipes = recipes[start:finish]

        return render_template(
            "profile.html", user=user, recipes=show_recipes,
            page=page, count=count, search=False)
    else:
        return redirect(url_for("login"))

    return render_template(
        "profile.html", user=user, recipes=recipes
    )


@app.route("/edit_profile/<username>", methods=["GET", "POST"])
def edit_profile(username):

    user = mongo.db.users.find_one(
        {"username": session["user"]})

    if not actual_user(username.lower()):
        return redirect(url_for("login"))

    # Update profile function
    if request.method == "POST":
        submit = {
            "username": user["username"],
            "password": user["password"],
            "user_img": user["user_img"],
        }
        mongo.db.users.update({"username": session["user"]}, submit)
        flash("Profile Updated")

        return render_template("profile.html", user=user)

    if "user" in session:
        return render_template("edit_profile.html", user=user)

    return redirect(url_for("login"))


@app.route("/articles")
def articles():
    return render_template("articles.html")


@app.route("/logout")
def logout():
    # User session cookies removal
    flash("See you soon Chef!")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/delete_profile/<username>")
def delete_profile(username):

    mongo.db.users.remove({"username": username.lower()})
    flash("Profile Deleted")
    session.pop("user")

    return redirect(url_for("register"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        recipe = {
            "recipe_name": request.form.get("recipe_name"),
            "category_name": request.form.get("category_name"),
            "prep_time": request.form.get("prep_time"),
            "difficulty": request.form.get("difficulty"),
            "description": request.form.get("description"),
            "ingredients": request.form.get("ingredients"),
            "preparation": request.form.get("preparation"),
            "recipe_image": request.form.get("recipe_image"),
            "created_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipe)
        flash("Recipe Shared!")
        return redirect(url_for("get_recipes", search=""))

    return render_template("add_recipe.html")


@app.route("/recipe/<recipe_id>")
def recipe(recipe_id):
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    print(recipe)
    return render_template("recipe.html", recipe=recipe)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):

    recipe_data = mongo.db.recipes.find_one(
        {"_id": ObjectId(recipe_id)})

    if not actual_user(recipe_data["created_by"]):
        return redirect(url_for("login"))

    if request.method == "POST":
        submit = {
            "recipe_name": request.form.get("recipe_name"),
            "category_name": request.form.get("category_name"),
            "prep_time": request.form.get("prep_time"),
            "difficulty": request.form.get("difficulty"),
            "description": request.form.get("description"),
            "ingredients": request.form.get("ingredients"),
            "preparation": request.form.get("preparation"),
            "recipe_image": request.form.get("recipe_image"),
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Recipe Improved!")

        return redirect(url_for("get_recipes", search='', recipe_id=recipe_id))

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})

    # Check for the user to match in order to Edit the Recipe
    if "user" in session.keys():
        user = session["user"].lower()

        if user == session["user"].lower():
            return render_template("edit_recipe.html", recipe=recipe)

        else:
            return redirect(url_for("get_recipes", search=""))

    else:
        return redirect(url_for("login"))


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("Recipe Deleted")
    return redirect(url_for("get_recipes", search=""))




if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
