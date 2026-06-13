import asyncio
import motor.motor_asyncio
import pprint

async def main():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["careerpilot"]
    cursor = db["resumes"].find().sort("_id", -1).limit(5)
    async for resume in cursor:
        filename = resume.get("filename")
        exp = resume.get("parsed_data", {}).get("experience", [])
        print(f"File: {filename}, Experience Count: {len(exp)}")

asyncio.run(main())
