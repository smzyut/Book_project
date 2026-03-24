import os
import random
import requests
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
# from supabase import create_client,Client

app = FastAPI(title="Book Discovery  API")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_headers(return_representation=False):
    headers={
        "apikey":SUPABASE_KEY,
        "Authorization":f"Bearer {SUPABASE_KEY}",
        "Content-Type":"application/json"
    }
    if return_representation:
        headers["Prefer"] = "return=representation"
    return headers

class TagCreate(BaseModel):
    name:str=Field(...,min_length=1,max_length=50,description="興味のあるキーワード")

class BookSave(BaseModel):
    title:str=Field(...,min_length=1)
    authors:str | None=None
    thumbnails:str | None=None
    tag_id:int | None=None

class BookUpdate(BaseModel):
    status:str=Field(...,pattern="^(want_to_read|reading|finished)$")
    
@app.post("/tags/",status_code=201)
def create_tag(tag:TagCreate):
    # data=supabase.table("tags").insert(tag.model.dump()).execute()
    # return data.data[0]
    url = f"{SUPABASE_URL}/rest/v1/tags"
    headers = get_supabase_headers(return_representation=True)
    
    response = requests.post(url,headers=headers,json=tag.model_dump())
    
    if response.status_code not in (200,201):
        raise HTTPException(status_code=400,detail=f"タグの登録に失敗しました:{response.text}")
    
    return response.json()[0]

@app.get("/discover/")
def discover_books():
    # tags_data = supabase.table("tags").select("*").execute()
    url = f"{SUPABASE_URL}/rest/v1/tags?select=*"
    headers=get_supabase_headers()
    
    tags_response = requests.get(url,headers=headers)
    if tags_response.status_code != 200 or not tags_response.json():
        raise HTTPException(status_code=404,detail="まずは/tags/から興味のあるキーワードを登録してください")
    tags_data = tags_response.json()
    
    selected_tag = random.choice(tags_data)
    keyword = selected_tag["name"]
    
    google_books_url = f"https://www.googleapis.com/books/v1/volumes?q={keyword}&maxResults=3&orderBy=newest"
    response = requests.get(google_books_url)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500,detail="本の検索に失敗しました")
    
    books = response.json().get("items",[])
    
    recommendations = []
    for book in books:
        info = book.get("volumeInfo",{})
        recommendations.append({
            "suggested_by_tag":keyword,
            "tag_id":selected_tag["id"],
            "title":info.get("title","タイトル不明"),
            "authors":",".join(info.get("authors",["著者不明"])),
            "descriptions":info.get("descriptions","説明なし")[:100] + "...",
            "thumbnail_url":info.get("imageLinks",{}).get("thumbnail")
        })
    
    return {"message":f"「{keyword}」に関するおすすめの本です！","books":recommendations}

@app.post("/books/",status_code=201)
def save_book(book:BookSave):
    # data = supabase.table("saved_books").insert(book.model_dump()).execute()
    # return data.data[0]
    url = f"{SUPABASE_URL}/rest/v1/saved_books"
    headers = get_supabase_headers(return_representation=True)
    
    response = requests.post(url,headers=headers,json=book.model_dump())
    
    if response.status_code not in (200,201):
        raise HTTPException(status_code=400,detail=f"保存に失敗しました:{response.text}")
    
    return response.json()[0]

@app.patch("/books/{book_id}")
def update_book_status(book_id:int,book_update:BookUpdate):
    # data = supabase.table("saved_books").update({"status":book_update.status}).eq("id",book_id).execute()
    url = f"{SUPABASE_URL}/rest/v1/saved_books?id=eq.{book_id}"
    headers = get_supabase_headers(return_representation=True)
    
    response= requests.patch(url,headers=headers,json={"status":book_update.status})
    
    if response.status_code != 200 or not response.json():
        raise HTTPException(status_code=404,detail='指定された本が見つからないか、更新に失敗しました')
    
    return response.json()[0]