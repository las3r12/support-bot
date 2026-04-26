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
    {
        "id": "pride-and-prejudice",
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "price": 9.99,
        "cover": "https://covers.openlibrary.org/b/id/8739161-L.jpg",
        "genre": "Romantic Fiction",
        "pages": 432,
        "published": 1813,
        "isbn": "978-0-14-143951-8",
        "description": (
            "When the Bennet family's five daughters need husbands, the arrival of "
            "wealthy Mr. Bingley and his aloof friend Mr. Darcy sets hearts racing "
            "and tongues wagging. Elizabeth Bennet, the sharpest of the sisters, "
            "clashes with Darcy in a battle of wits that slowly gives way to "
            "something deeper. Austen's most beloved novel is a razor-sharp comedy "
            "of manners and one of literature's greatest love stories."
        ),
    },
    {
        "id": "moby-dick",
        "title": "Moby-Dick",
        "author": "Herman Melville",
        "price": 13.99,
        "cover": "https://covers.openlibrary.org/b/id/8091016-L.jpg",
        "genre": "Adventure Fiction",
        "pages": 635,
        "published": 1851,
        "isbn": "978-0-14-243723-7",
        "description": (
            "Call me Ishmael. So begins one of the most ambitious novels in the "
            "English language. Sailor Ishmael joins the crew of the Pequod, captained "
            "by the obsessive Ahab, who is hell-bent on hunting the white whale that "
            "took his leg. Part adventure, part philosophical meditation, Melville's "
            "epic is a towering exploration of obsession, fate, and humanity's "
            "struggle against nature."
        ),
    },
    {
        "id": "the-odyssey",
        "title": "The Odyssey",
        "author": "Homer",
        "price": 10.49,
        "cover": "https://covers.openlibrary.org/b/id/8114609-L.jpg",
        "genre": "Epic Poetry",
        "pages": 374,
        "published": -800,
        "isbn": "978-0-14-044911-2",
        "description": (
            "After ten years fighting in Troy, the cunning hero Odysseus faces ten "
            "more years of perilous voyaging before he can return home to Ithaca. "
            "Facing cyclops, sirens, sea monsters, and the wrath of gods, his journey "
            "home becomes the definitive story of endurance and homecoming. Homer's "
            "epic poem, written around 800 BC, is the foundation of Western "
            "storytelling."
        ),
    },
    {
        "id": "don-quixote",
        "title": "Don Quixote",
        "author": "Miguel de Cervantes",
        "price": 15.49,
        "cover": "https://covers.openlibrary.org/b/id/8221822-L.jpg",
        "genre": "Satirical Fiction",
        "pages": 863,
        "published": 1605,
        "isbn": "978-0-06-093434-8",
        "description": (
            "A middle-aged nobleman so consumed by tales of chivalry that he renames "
            "himself Don Quixote and sets out as a knight-errant, accompanied by his "
            "loyal squire Sancho Panza. Together they tilt at windmills, mistake "
            "inns for castles, and blunder through a Spain that has no room for their "
            "idealism. Widely considered the first modern novel and one of the "
            "greatest works ever written."
        ),
    },
    {
        "id": "jane-eyre",
        "title": "Jane Eyre",
        "author": "Charlotte Brontë",
        "price": 10.99,
        "cover": "https://covers.openlibrary.org/b/id/8739185-L.jpg",
        "genre": "Gothic Fiction",
        "pages": 507,
        "published": 1847,
        "isbn": "978-0-14-144114-6",
        "description": (
            "Orphaned Jane Eyre grows up plain, poor, and fiercely principled. As "
            "governess at Thornfield Hall she falls for her brooding employer "
            "Mr. Rochester — but the house holds a terrible secret. Brontë's "
            "landmark novel was revolutionary in placing a woman's inner moral life "
            "at the centre of the story, and its passion and atmosphere have never "
            "dimmed."
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


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, port=5001, host="0.0.0.0")
