from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.ai_service import ask_ai
from app.services.product_service import get_products
from app.services.vision_service import (
    analyze_room,
    ALLOWED_CONTENT_TYPES,
    MAX_IMAGE_SIZE_BYTES,
)
from app.services.render_service import render_product_in_room
from app.services.nano_render_service import (
    generate_room_render,
    generate_ai_design,
)



app = FastAPI(
    title="Tabrano AI",
    version="1.0.0"
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



class ChatRequest(BaseModel):

    message: str

    history: list = Field(
        default_factory=list
    )




@app.get("/")
def home():

    return {
        "status": "ok",
        "message": "Tabrano AI Hazır!"
    }




@app.post("/chat")
def chat(request: ChatRequest):

    try:

        response = ask_ai(
            message=request.message,
            history=request.history
        )


        return response



    except Exception as e:

        print(
            "CHAT HATASI:",
            repr(e)
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )




@app.get("/products")
def products():

    return get_products()




@app.post("/analyze-room")
async def analyze_room_endpoint(
    image: UploadFile = File(...),
    client_id: str = Form(default="anonymous"),
    message: str = Form(default="")
):

    if image.content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Desteklenmeyen dosya formatı. "
                "Lütfen JPEG, PNG veya WEBP yükleyin."
            )
        )


    image_bytes = await image.read()


    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:

        raise HTTPException(
            status_code=400,
            detail="Dosya çok büyük. Lütfen 8MB altında bir görsel yükleyin."
        )


    try:

        result = analyze_room(
            image_bytes=image_bytes,
            content_type=image.content_type,
            client_id=client_id,
            user_message=message
        )


        return result



    except Exception as e:

        print(
            "ANALYZE ROOM HATASI:",
            repr(e)
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )




@app.post("/render-product")
async def render_product_endpoint(
    room_image: UploadFile = File(...),
    product_image_url: str = Form(...),
    product_name: str = Form(default="ürün"),
    client_id: str = Form(default="anonymous")
):

    if room_image.content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Desteklenmeyen dosya formatı. "
                "Lütfen JPEG, PNG veya WEBP yükleyin."
            )
        )


    room_image_bytes = await room_image.read()


    if len(room_image_bytes) > MAX_IMAGE_SIZE_BYTES:

        raise HTTPException(
            status_code=400,
            detail="Dosya çok büyük. Lütfen 8MB altında bir görsel yükleyin."
        )


    try:

        result = render_product_in_room(
            room_image_bytes=room_image_bytes,
            room_content_type=room_image.content_type,
            product_image_url=product_image_url,
            product_name=product_name,
            client_id=client_id
        )


        return result



    except Exception as e:

        print(
            "RENDER PRODUCT HATASI:",
            repr(e)
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )




@app.post("/render-product-nano")
async def render_product_nano_endpoint(
    room_image: UploadFile = File(...),
    product_image_url: str = Form(...),
    product_name: str = Form(default="ürün"),
    client_id: str = Form(default="anonymous")
):

    if room_image.content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Desteklenmeyen dosya formatı. "
                "Lütfen JPEG, PNG veya WEBP yükleyin."
            )
        )


    room_image_bytes = await room_image.read()


    if len(room_image_bytes) > MAX_IMAGE_SIZE_BYTES:

        raise HTTPException(
            status_code=400,
            detail="Dosya çok büyük. Lütfen 8MB altında bir görsel yükleyin."
        )


    try:

        result = generate_room_render(
            room_image_bytes=room_image_bytes,
            room_content_type=room_image.content_type,
            product_image_url=product_image_url,
            product_name=product_name,
            client_id=client_id
        )


        return result



    except Exception as e:

        print(
            "RENDER PRODUCT NANO HATASI:",
            repr(e)
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )




@app.post("/render-ai-design")
async def render_ai_design_endpoint(
    product_image_url: str = Form(...),
    style: str = Form(default=""),
    product_name: str = Form(default="ürün"),
    client_id: str = Form(default="anonymous")
):

    try:

        result = generate_ai_design(
            product_image=product_image_url,
            style=style,
            product_name=product_name,
            client_id=client_id
        )


        return result



    except Exception as e:

        print(
            "RENDER AI DESIGN HATASI:",
            repr(e)
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )