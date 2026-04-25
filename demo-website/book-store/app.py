from flask import Flask, render_template, abort

app = Flask(__name__)

BOOKS = [
    {
        "id": "1984",
        "title": "1984",
        "author": "George Orwell",
        "price": 12.99,
        "cover": "https://covers.openlibrary.org/b/id/8575708-L.jpg",
        "genre": "Dystopian Fiction",
        "pages": 328,
        "published": 1949,
        "isbn": "978-0-452-28423-4",
        "description": (
            "A chilling vision of a totalitarian society where Big Brother watches "
            "every move. Winston Smith works for the Ministry of Truth, rewriting "
            "history to match the Party's ever-changing version of reality. When he "
            "begins a forbidden love affair and dares to think for himself, the "
            "consequences are devastating. A timeless warning about the dangers of "
            "unchecked power and the fragility of truth."
        ),
    },
    {
        "id": "to-kill-a-mockingbird",
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "price": 11.49,
        "cover": "https://covers.openlibrary.org/b/id/8228691-L.jpg",
        "genre": "Southern Gothic",
        "pages": 281,
        "published": 1960,
        "isbn": "978-0-06-112008-4",
        "description": (
            "Told through the eyes of young Scout Finch in 1930s Alabama, this "
            "Pulitzer Prize-winning novel follows her father Atticus Finch, a "
            "lawyer who defends a Black man falsely accused of a terrible crime. "
            "A profound exploration of racial injustice, moral growth, and the "
            "loss of innocence that remains as relevant today as ever."
        ),
    },
    {
        "id": "the-great-gatsby",
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "price": 10.99,
        "cover": "https://covers.openlibrary.org/b/id/7920839-L.jpg",
        "genre": "Literary Fiction",
        "pages": 180,
        "published": 1925,
        "isbn": "978-0-7432-7356-5",
        "description": (
            "Set in the glittering Jazz Age of Long Island, Nick Carraway narrates "
            "the rise and fall of his mysterious neighbour Jay Gatsby, a self-made "
            "millionaire obsessed with rekindling his romance with the beautiful "
            "Daisy Buchanan. Fitzgerald's masterpiece dissects the American Dream, "
            "wealth, illusion, and the impossibility of recapturing the past."
        ),
    },
    {
        "id": "brave-new-world",
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "price": 13.49,
        "cover": "https://covers.openlibrary.org/b/id/8406786-L.jpg",
        "genre": "Dystopian Fiction",
        "pages": 311,
        "published": 1932,
        "isbn": "978-0-06-085052-4",
        "description": (
            "In a future World State, citizens are engineered from birth and "
            "conditioned to be happy consumers. Bernard Marx feels out of place "
            "in this comfortable nightmare and brings a 'Savage' from a Reservation "
            "into civilisation — with explosive results. Huxley's prescient satire "
            "on consumerism, conformity, and the cost of manufactured happiness."
        ),
    },
    {
        "id": "the-catcher-in-the-rye",
        "title": "The Catcher in the Rye",
        "author": "J.D. Salinger",
        "price": 10.49,
        "cover": "https://covers.openlibrary.org/b/id/8231432-L.jpg",
        "genre": "Literary Fiction",
        "pages": 277,
        "published": 1951,
        "isbn": "978-0-316-76948-0",
        "description": (
            "Holden Caulfield has just been expelled from prep school and spends "
            "three days wandering New York City, raging against the phoniness of "
            "the adult world. Salinger's iconic coming-of-age novel captures "
            "adolescent alienation, grief, and the painful transition to adulthood "
            "with unflinching honesty and a voice that has never dated."
        ),
    },
    {
        "id": "crime-and-punishment",
        "title": "Crime and Punishment",
        "author": "Fyodor Dostoevsky",
        "price": 14.99,
        "cover": "https://covers.openlibrary.org/b/id/8765370-L.jpg",
        "genre": "Psychological Fiction",
        "pages": 551,
        "published": 1866,
        "isbn": "978-0-14-044913-6",
        "description": (
            "Raskolnikov, a destitute student in St. Petersburg, convinces himself "
            "that extraordinary men are above conventional morality — and murders a "
            "pawnbroker to prove it. What follows is a shattering psychological "
            "portrait of guilt, paranoia, and redemption. Dostoevsky's masterwork "
            "is one of the greatest novels ever written."
        ),
    },
    {
        "id": "the-alchemist",
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "price": 11.99,
        "cover": "https://covers.openlibrary.org/b/id/8297409-L.jpg",
        "genre": "Philosophical Fiction",
        "pages": 197,
        "published": 1988,
        "isbn": "978-0-06-231500-7",
        "description": (
            "Santiago, an Andalusian shepherd boy, dreams of finding treasure near "
            "the Egyptian pyramids and sets off on a journey across continents. "
            "Along the way he meets an alchemist who teaches him to listen to his "
            "heart and follow his Personal Legend. A beloved fable about pursuing "
            "your dreams and finding meaning in the journey itself."
        ),
    },
]

BOOK_INDEX = {b["id"]: b for b in BOOKS}


@app.route("/")
def index():
    return render_template("index.html", books=BOOKS)


@app.route("/book/<book_id>")
def book(book_id):
    b = BOOK_INDEX.get(book_id)
    if not b:
        abort(404)
    return render_template("book.html", book=b)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, port=5001)
