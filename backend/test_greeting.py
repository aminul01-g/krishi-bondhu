import asyncio
from app.main import greetings

def test():
    msg = "hello"
    clean = msg.lower().strip()
    if clean in greetings:
        return "হ্যালো! আমি আপনার কৃষিবন্ধু। আমি কীভাবে সাহায্য করতে পারি? (Hello! I'm your KrishiBondhu. How can I help you today?)"
    return "Not a greeting"

print("User: hello")
print(f"Agent: {test()}")

print("\nUser: হ্যালো")
msg = "হ্যালো"
print(f"Agent: {test() if msg.lower().strip() in greetings else 'Not a greeting'}")
