from faker import Faker
from uuid import uuid4

fake = Faker()

categories = [
    "Electronics",
    "Books",
    "Fashion",
    "Home",
    "Sports"
]

for _ in range(5):
    print(
        {
            "id": str(uuid4()),
            "name": fake.word(),
            "category": fake.random_element(categories),
            "price": round(fake.random_number(digits=4)/10,2)
        }
    )