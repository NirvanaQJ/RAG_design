from database import SessionLocal, init_db, User, UserRole
from auth import hash_password


def seed_users():
    init_db()
    db = SessionLocal()

    existing_admin = db.query(User).filter(User.username == "admin").first()
    if not existing_admin:
        admin = User(
            username="admin",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        print("默认管理员账号已创建: admin / admin123")

    existing_student = db.query(User).filter(User.username == "student").first()
    if not existing_student:
        student = User(
            username="student",
            hashed_password=hash_password("student123"),
            role=UserRole.STUDENT,
        )
        db.add(student)
        print("默认学生账号已创建: student / student123")

    db.commit()
    db.close()
    print("数据库初始化完成！")


if __name__ == "__main__":
    seed_users()
