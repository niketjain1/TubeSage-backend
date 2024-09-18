from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

openai.api_key = os.getenv("OPENAI_API_KEY")

class VideoRequest(BaseModel):
    url: str

class QuestionRequest(BaseModel):
    url: str
    question: str
    chat_history: list

# Global variable to store transcripts
transcripts = {}

def extract_video_id(url):
    return url.split("v=")[-1]

def get_transcript(video_id):
    if video_id in transcripts:
        return transcripts[video_id]
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'hi', 'es', 'fr', 'de', 'ja', 'ko', 'ru'])
        full_transcript = " ".join([entry['text'] for entry in transcript])
        transcripts[video_id] = full_transcript
        return full_transcript
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transcript")
async def fetch_transcript(request: VideoRequest):
    video_id = extract_video_id(request.url)
    transcript = get_transcript(video_id)
    return {"transcript": transcript}

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    video_id = extract_video_id(request.url)
    
    if video_id not in transcripts:
        transcript = get_transcript(video_id)
    else:
        transcript = transcripts[video_id]
    
    messages = [
        {"role": "system", "content": "You are a youtube question answerer assitant that answers questions based on the provided video transcript. Keep the answer short and concise. Don't mention the keyword 'transcript' while answering the question. The answer should be in first person. If the question is not related to the video, say respond with 'I'm sorry, I can't answer that question. Its out of context.'"},
        {"role": "user", "content": f"Transcript: {transcript}"}
    ]
    
    # Add chat history
    messages.extend(request.chat_history)
    
    # Add the new question
    messages.append({"role": "user", "content": request.question})
    
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages
    )
    
    answer = response.choices[0].message['content']
    
    return {"answer": answer, "updated_history": messages + [{"role": "assistant", "content": answer}]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)