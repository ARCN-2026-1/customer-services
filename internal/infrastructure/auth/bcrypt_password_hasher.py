import bcrypt


class BcryptPasswordHasher:
    def hash(self, plain_password: str) -> str:
        encoded_password = plain_password.encode("utf-8")
        return bcrypt.hashpw(encoded_password, bcrypt.gensalt()).decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
