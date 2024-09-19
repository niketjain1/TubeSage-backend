from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
from .models import VideoRequest, QuestionRequest, ActionRequest
import os
import openai

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

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
        {"role": "system", "content": "You are a youtube question answerer assitant that answers questions based on the provided video transcript. Keep the answer short and concise in english. Don't mention the keyword 'transcript' while answering the question. The answer should be in first person. If the question is not related to the video, say respond with 'I'm sorry, I can't answer that question. Its out of context.'"},
        {"role": "user", "content": f"Transcript: {transcript}"}
    ]
    
    # Add chat history
    messages.extend(request.chat_history)
    
    # Add the new question
    messages.append({"role": "user", "content": request.question})
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    answer = response.choices[0].message['content']
    
    return {"answer": answer, "updated_history": messages + [{"role": "assistant", "content": answer}]}

@app.post("/action")
async def perform_action(request: ActionRequest):
    video_id = extract_video_id(request.url)
    
    if video_id not in transcripts:
        transcript = get_transcript(video_id)
    else:
        transcript = transcripts[video_id]
    
    action_prompts = {
        "summarize": "Provide a brief summary of the video content in about 3-4 sentences.",
        "key-points": "List the 3-5 main key points or takeaways from the video.",
        "explain": "Provide a detailed explanation of the main topic discussed in the video.",
        "related-topics": "Suggest 3-5 related topics that viewers might want to explore further based on this video's content."
    }
    
    if request.action not in action_prompts:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    messages = [
        {"role": "system", "content": "You are a youtube video analysis assistant. Provide concise and informative responses based on the video transcript."},
        {"role": "user", "content": f"Transcript: {transcript}\n\nTask: {action_prompts[request.action]}"}
    ]
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    result = response.choices[0].message['content']
    
    return {"result": result}

@app.post("/suggested_questions")
async def generate_suggested_questions(request: VideoRequest):
    video_id = extract_video_id(request.url)
    
    if video_id not in transcripts:
        transcript = get_transcript(video_id)
    else:
        transcript = transcripts[video_id]
    
    messages = [
        {"role": "system", "content": "You are a youtube video analysis assistant. Generate 3-5 short, precise, and specific questions based on the video transcript. Each question should be no longer than 10 words and should encourage viewers to engage more deeply with the video content. The questions should only be in english."},
        {"role": "user", "content": f"Transcript: {transcript}\n\nTask: Generate 3-5 suggested questions about this video content."}
    ]
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    questions = response.choices[0].message['content'].split('\n')
    questions = [q.strip() for q in questions if q.strip()]
    
    return {"questions": questions}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)