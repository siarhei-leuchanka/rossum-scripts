import asyncio
from asyncio import gather


async def gather_throttled(tasks: list, sleep_limit: int, sleep_time: int) -> dict:
    annotation_contents = []
    task_accumulator = []

    for i, arg in enumerate(tasks):
        task_accumulator.append(arg)
        if i % sleep_limit == 0 and i != 0:
            print("Sleeping")
            await asyncio.sleep(sleep_time)
            task_bucket = task_accumulator.copy()
            annotation_contents.extend(await asyncio.gather(*task_bucket))
            task_accumulator.clear()

    # Gather remaining tasks if task_bucket is not empty
    if task_accumulator:
        annotation_contents.extend(await asyncio.gather(*task_accumulator))

    return annotation_contents
