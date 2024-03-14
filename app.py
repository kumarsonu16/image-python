import pandas as pd
from PIL import Image
from flask import Flask, request, jsonify
import numpy as np
import cv2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, LargeBinary
import os
from io import BytesIO

# Define Flask app
app = Flask(__name__)

# Define SQLAlchemy Base
Base = declarative_base()

# Define Image model
class ImageFrame(Base):
    __tablename__ = 'image_frames'
    id = Column(Integer, primary_key=True)
    depth = Column(Integer)
    image_data = Column(LargeBinary)

# Function to resize image
def resize_image(image, new_width):
    original_width, original_height = image.size
    print("Original Image Dimensions:", (original_width, original_height))

    if original_width == 0 or original_height == 0:
        raise ValueError("Original image dimensions are invalid")
    
    aspect_ratio = float(new_width) / original_width
    new_height = int(original_height * aspect_ratio)
    print("New Image Dimensions:", (new_width, new_height))
    print("Original Image Dimensions 2 :", image.size)
    print("New Image Dimensions 2:", (new_width, new_height))

    if new_height <= 0:
        raise ValueError("Invalid new height after resizing")
    
    resized_image = image.resize((new_width, new_height))
    return resized_image


# Function to apply custom color map
def apply_custom_color_map(image):
    custom_colormap = cv2.applyColorMap(image, cv2.COLORMAP_JET)
    return custom_colormap

# Read CSV and store images in database
def process_csv(csv_file, db_uri):
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    df = pd.read_csv(csv_file)

    for index, row in df.iterrows():
        depth = row['depth']
        pixel_data = row.drop('depth').values
        print("Pixel Data:", pixel_data)  # Print the pixel data
        # Reshape pixel data into a 2D array representing the image
        image_array = pixel_data.reshape((1, -1)).astype(np.uint8)
        print("Original Image Dimensions:", image_array.shape)
        # Convert the array to an image
        image = Image.fromarray(image_array)
        print("Image Dimensions:", image.size)
        # Resize the image
        resized_image = image.resize((150, 150))
        print("Resized Image Dimensions:", resized_image.size)
        # Convert the resized image to bytes
        with BytesIO() as buffer:
            resized_image.save(buffer, format="JPEG")
            resized_image_bytes = buffer.getvalue()

        image_frame = ImageFrame(depth=depth, image_data=resized_image_bytes)
        session.add(image_frame)

    session.commit()
    session.close()

# API endpoint to request image frames
@app.route('/image_frames', methods=['GET'])
def get_image_frames():
    depth_min = int(request.args.get('depth_min'))
    depth_max = int(request.args.get('depth_max'))

    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    frames = session.query(ImageFrame).filter(ImageFrame.depth >= depth_min, ImageFrame.depth <= depth_max).all()
    session.close()

    frame_responses = []
    for frame in frames:
        frame_data = np.frombuffer(frame.image_data, dtype=np.uint8)
        frame_image = cv2.imdecode(frame_data, cv2.IMREAD_GRAYSCALE)
        
        # Apply custom color map
        colormap_frame = apply_custom_color_map(frame_image)
        
        frame_responses.append(colormap_frame.tolist())

    return jsonify(frame_responses)

if __name__ == '__main__':
    csv_file = 'image_data.csv'
    db_uri = 'sqlite:///image_frames.db'
    process_csv(csv_file, db_uri)
    app.run(debug=True)  # Run Flask app
