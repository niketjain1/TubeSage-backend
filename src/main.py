from fastapi import FastAPI, HTTPException
from models import VideoRequest, QuestionRequest
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.post("/transcript")
async def get_transcript(request: VideoRequest):
    video_id = extract_video_id(request.url)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return {"transcript": " ".join([entry['text'] for entry in transcript])}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    transcript = await get_transcript(VideoRequest(url=request.url))
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided transcript."},
            {"role": "user", "content": f"Transcript: {transcript['transcript']}\n\nQuestion: {request.question}"}
        ]
    )
    
    return {"answer": response.choices[0].message['content']}

@app.get("/")
def read_root():
    return {"message": "Welcome to the YouTube Transcript API"}


def extract_video_id(url):
    return url.split("v=")[-1]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)