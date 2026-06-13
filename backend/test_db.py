import asyncio
import motor.motor_asyncio
import pprint

async def main():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["careerpilot"]
    resume = await db["resumes"].find_one(sort=[("_id", -1)])
    if resume:
        pprint.pprint(resume["parsed_data"]["experience"])
    else:
        print("No resume found")

asyncio.run(main())
