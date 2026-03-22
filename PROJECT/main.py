from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()


books = [
    {"id": 1, "title": "Python Basics", "author": "John", "genre": "Tech", "is_available": True},
    {"id": 2, "title": "History of India", "author": "Raj", "genre": "History", "is_available": True},
    {"id": 3, "title": "AI Guide", "author": "Sam", "genre": "Tech", "is_available": False},
    {"id": 4, "title": "Science 101", "author": "Ravi", "genre": "Science", "is_available": True},
    {"id": 5, "title": "Fiction World", "author": "Anu", "genre": "Fiction", "is_available": True},
    {"id": 6, "title": "Data Structures", "author": "Kiran", "genre": "Tech", "is_available": True},
]

borrow_records = []
record_counter = 1
queue = []


@app.get("/")
def home():
    return {"message": "Welcome to City Public Library"}


@app.get("/books")
def get_books():
    available = [b for b in books if b["is_available"]]
    return {
        "books": books,
        "total": len(books),
        "available_count": len(available)
    }


@app.get("/books/summary")
def summary():
    available = [b for b in books if b["is_available"]]
    borrowed = [b for b in books if not b["is_available"]]

    genre_count = {}
    for b in books:
        genre_count[b["genre"]] = genre_count.get(b["genre"], 0) + 1

    return {
        "total": len(books),
        "available": len(available),
        "borrowed": len(borrowed),
        "genre_breakdown": genre_count
    }

def filter_books_logic(genre, author, is_available):
    result = books

    if genre is not None:
        result = [b for b in result if b["genre"] == genre]

    if author is not None:
        result = [b for b in result if b["author"] == author]

    if is_available is not None:
        result = [b for b in result if b["is_available"] == is_available]

    return result

@app.get("/books/filter")
def filter_books(
    genre: Optional[str] = None,
    author: Optional[str] = None,
    is_available: Optional[bool] = None
):
    result = filter_books_logic(genre, author, is_available)
    return {"books": result, "count": len(result)}


@app.get("/books/search")
def search_books(keyword: str):
    result = [
        b for b in books
        if keyword.lower() in b["title"].lower()
        or keyword.lower() in b["author"].lower()
    ]

    if not result:
        return {"message": f"No books found for: {keyword}"}

    return {"total_found": len(result), "books": result}


@app.get("/books/sort")
def sort_books(sort_by: str = "title", order: str = "asc"):

    if sort_by not in ["title", "author", "genre"]:
        raise HTTPException(400, "Invalid sort_by")

    if order not in ["asc", "desc"]:
        raise HTTPException(400, "Invalid order")

    return {
        "sort_by": sort_by,
        "order": order,
        "books": sorted(books, key=lambda b: b[sort_by], reverse=(order == "desc"))
    }


@app.get("/books/page")
def paginate(page: int = 1, limit: int = 3):
    start = (page - 1) * limit

    return {
        "page": page,
        "limit": limit,
        "total": len(books),
        "total_pages": -(-len(books) // limit),
        "books": books[start:start + limit]
    }


@app.get("/books/browse")
def browse(
    keyword: Optional[str] = None,
    sort_by: str = "title",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):

    result = books

    if keyword:
        result = [
            b for b in result
            if keyword.lower() in b["title"].lower()
            or keyword.lower() in b["author"].lower()
        ]

    result = sorted(result, key=lambda b: b[sort_by], reverse=(order == "desc"))

    start = (page - 1) * limit

    return {
        "keyword": keyword,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit,
        "total_found": len(result),
        "total_pages": -(-len(result) // limit),
        "books": result[start:start + limit]
    }


@app.get("/borrow-records")
def get_records():
    return {
        "records": borrow_records,
        "total": len(borrow_records)
    }


@app.get("/borrow-records/search")
def search_records(member_name: str):
    result = [
        r for r in borrow_records
        if member_name.lower() in r["member_name"].lower()
    ]

    if not result:
        return {"message": f"No records for {member_name}"}

    return {"records": result, "count": len(result)}

@app.get("/borrow-records/page")
def page_records(page: int = 1, limit: int = 2):
    start = (page - 1) * limit

    return {
        "page": page,
        "limit": limit,
        "total": len(borrow_records),
        "total_pages": -(-len(borrow_records) // limit),
        "records": borrow_records[start:start + limit]
    }


class BorrowRequest(BaseModel):
    member_name: str = Field(..., min_length=2)
    book_id: int = Field(..., gt=0)
    borrow_days: int = Field(..., gt=0, le=60)
    member_id: str = Field(..., min_length=4)
    member_type: str = "regular"

def find_book(book_id):
    for b in books:
        if b["id"] == book_id:
            return b
    return None

def calculate_due_date(days, member_type):
    if member_type == "premium":
        days = min(days, 60)
    else:
        days = min(days, 30)
    return f"Return by: Day {15 + days}"


@app.post("/borrow")
def borrow_book(data: BorrowRequest):
    global record_counter

    book = find_book(data.book_id)

    if not book:
        raise HTTPException(404, "Book not found")

    if not book["is_available"]:
        raise HTTPException(400, "Book already borrowed")

    book["is_available"] = False

    record = {
        "record_id": record_counter,
        "member_name": data.member_name,
        "book": book["title"],
        "due": calculate_due_date(data.borrow_days, data.member_type)
    }

    borrow_records.append(record)
    record_counter += 1

    return record

class NewBook(BaseModel):
    title: str = Field(..., min_length=2)
    author: str = Field(..., min_length=2)
    genre: str = Field(..., min_length=2)
    is_available: bool = True

@app.post("/books", status_code=201)
def add_book(book: NewBook):
    for b in books:
        if b["title"].lower() == book.title.lower():
            raise HTTPException(400, "Duplicate book")

    new = {"id": len(books) + 1, **book.dict()}
    books.append(new)
    return new


@app.post("/queue/add")
def add_queue(member_name: str, book_id: int):
    book = find_book(book_id)

    if not book:
        raise HTTPException(404, "Book not found")

    if book["is_available"]:
        return {"message": "Book is available, no need to queue"}

    queue.append({"member": member_name, "book_id": book_id})

    return {"message": "Added to queue"}

@app.get("/queue")
def get_queue():
    return queue


@app.post("/return/{book_id}")
def return_book(book_id: int):
    global record_counter

    book = find_book(book_id)

    if not book:
        raise HTTPException(404, "Book not found")

    book["is_available"] = True

    for q in queue:
        if q["book_id"] == book_id:
            queue.remove(q)

            book["is_available"] = False

            record = {
                "record_id": record_counter,
                "member_name": q["member"],
                "book": book["title"],
                "due": "Auto assigned"
            }

            borrow_records.append(record)
            record_counter += 1

            return {"message": "returned and re-assigned"}

    return {"message": "returned and available"}


@app.get("/books/{book_id}")
def get_book(book_id: int):
    book = find_book(book_id)
    if not book:
        return {"error": "Book not found"}
    return book


@app.put("/books/{book_id}")
def update_book(
    book_id: int,
    genre: Optional[str] = None,
    is_available: Optional[bool] = None
):
    book = find_book(book_id)

    if not book:
        raise HTTPException(404, "Book not found")

    if genre is not None:
        book["genre"] = genre

    if is_available is not None:
        book["is_available"] = is_available

    return book

@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    book = find_book(book_id)

    if not book:
        raise HTTPException(404, "Book not found")

    books.remove(book)
    return {"message": f"{book['title']} deleted"}
