"""
Seed script — run once to populate the database with test data.

Usage:
    python seed.py
"""
import random
import sys
from datetime import date, timedelta

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.transaction import Transaction, TransactionType
from app.models.user import User, UserRole

# Create tables
Base.metadata.create_all(bind=engine)

CATEGORIES_INCOME = ["salary", "freelance", "investments", "bonus", "rental"]
CATEGORIES_EXPENSE = ["rent", "utilities", "groceries", "transport", "healthcare",
                      "entertainment", "subscriptions", "insurance"]


def seed():
    db = SessionLocal()
    try:
        # ── Users ──────────────────────────────────────────────────────────────
        users_data = [
            {"full_name": "Admin User", "email": "admin@finance.com",
             "password": "admin123", "role": UserRole.admin},
            {"full_name": "Analyst User", "email": "analyst@finance.com",
             "password": "analyst123", "role": UserRole.analyst},
            {"full_name": "Viewer User", "email": "viewer@finance.com",
             "password": "viewer123", "role": UserRole.viewer},
        ]

        created_users = []
        for u in users_data:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                print(f"  [skip] User {u['email']} already exists.")
                created_users.append(existing)
                continue
            user = User(
                full_name=u["full_name"],
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
            )
            db.add(user)
            db.flush()
            created_users.append(user)
            print(f"  [ok]   Created user: {u['email']} ({u['role'].value})")

        db.commit()
        admin_user = created_users[0]

        # ── Transactions ───────────────────────────────────────────────────────
        existing_tx_count = db.query(Transaction).count()
        if existing_tx_count > 0:
            print(f"  [skip] {existing_tx_count} transactions already exist.")
        else:
            today = date.today()
            transactions = []

            # Generate 6 months of sample data
            for i in range(180):
                tx_date = today - timedelta(days=i)

                # ~2 transactions per day on average
                if random.random() < 0.5:
                    continue

                tx_type = random.choice([TransactionType.income, TransactionType.expense])
                if tx_type == TransactionType.income:
                    category = random.choice(CATEGORIES_INCOME)
                    amount = round(random.uniform(500, 8000), 2)
                else:
                    category = random.choice(CATEGORIES_EXPENSE)
                    amount = round(random.uniform(50, 2000), 2)

                transactions.append(Transaction(
                    amount=amount,
                    type=tx_type,
                    category=category,
                    date=tx_date,
                    notes=f"Auto-generated seed record — {category}",
                    created_by=admin_user.id,
                ))

            db.bulk_save_objects(transactions)
            db.commit()
            print(f"  [ok]   Created {len(transactions)} sample transactions.")

        print("\nSeed complete. Test credentials:")
        print("  admin@finance.com   / admin123")
        print("  analyst@finance.com / analyst123")
        print("  viewer@finance.com  / viewer123")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
