import os
from flask import Flask, request, render_template_string, redirect, url_for, render_template, send_from_directory, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import moviepy.editor as mpy
import requests
import json
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__, static_folder='../styles', template_folder='../templates')

load_dotenv()


client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# HTML template as a string for demonstration purposes
form_html = """
<!DOCTYPE html>
<html lang="en">
    <head>
        <!-- Character Encoding -->
        <meta charset="UTF-8">
        
        <!-- Viewport for Responsive Web Design -->
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        
        <!-- SEO Meta Tags -->
        <meta name="description" content="A site that allows the user to input a script and get a video that can be uploaded to youtube using AI">
        <meta name="keywords" content="AI image generator, automatic video generator">
        <meta name="author" content="TaskTide">
    
        <link rel="icon" href="{{ url_for('static', filename='tasktide_favicon.jpg') }}" type="image/x-icon">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.0.0/dist/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
        <link rel="stylesheet" href="{{ url_for('static', filename='main.css') }}">
    
        <title>Your Website Title</title>
    </head>
    
    <body>
        <div id="loading-screen">
            Loading, please wait...
        </div>
        <section id="form-section">
            <h1>Input a script below</h1>
            <form id="form-input" action="/submit" method="post">
                <label for="title">Input title:</label>
                <input type="text" id="title" name="title" class="form-control" required placeholder="The title is..">
    
                <label for="script">Input script:</label>
                <textarea id="script" name="script" required class="form-control" rows="6" placeholder="The quiet little girl..."></textarea>
                <div class="char-count" id="char-count"><span id="char-count"></span> characters remaining</div>

                <label for="captions">Do you want captions:</label>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="captions" value="yesCaptions" checked>
                    <label class="form-check-label" for="exampleRadios1">
                      Yes
                    </label>
                </div>
                 <div class="form-check">
                    <input class="form-check-input" type="radio" name="captions" id="exampleRadios2" value="noCaptions">
                    <label class="form-check-label" for="exampleRadios2">
                        No
                    </label>
                </div>
    
                <button type="submit" class="btn btn-primary" onclick="displayLoading()">Generate Video <i class='fa fa-star-o'></i></button>
            </form>
        </section>
        <script>
          function displayLoading(){
            document.getElementById("loading-screen").style.display = "block";
          }
        </script>
        <script>
            const tier = 'h'
            const textarea = document.getElementById('script');
            const charCount = document.getElementById('char-count');
            let maxLength

            if(tier == 'f'){
                // Set the maxlength attribute dynamically
                maxLength = 500;
            }
            else if(tier == 'l'){
                // Set the maxlength attribute dynamically
                maxLength = 1000;
            }
            else if(tier == 'm'){
                // Set the maxlength attribute dynamically
                maxLength = 2000;
            }
            else if(tier == 'h'){
                // Set the maxlength attribute dynamically
                maxLength = 3000;
            }

            // Set the maxlength attribute dynamically
            textarea.setAttribute('maxlength', maxLength);

            // Display the initial character count
            charCount.textContent = `${maxLength} characters remaining`;
    
            textarea.addEventListener('input', () => {
                const remaining = maxLength - textarea.value.length;
                charCount.textContent = `${remaining} characters remaining`;
            });
        </script>
        <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/popper.js@1.12.9/dist/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.0.0/dist/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
    </body>    
</html>
"""

def tokenize_by_full_stop(text):
    # Split the text by full stops
    tokens = text.split('.')
    # Remove any leading or trailing whitespace and discard empty tokens
    tokens = [token.strip() for token in tokens if token.strip()]
    return tokens

def generate_prompt_for_image(sentence):
    return f"Convert the following sentence into an image generation prompt that can be fed to an image generation AI model and create an image related to the sentence: {sentence}"

def call_openai_api(prompt):
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-3.5-turbo",
    )
    return response.choices[0].message.content

def generate_image(prompt_text):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt_text,
        size="1792x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    return image_url

def generate_text_image(text, width, height, fontsize=24):
    # Create a blank image with black background
    img = Image.new('RGB', (width, height), color='black')
    d = ImageDraw.Draw(img)

    # Load a font
    try:
        font = ImageFont.truetype("arial.ttf", fontsize)
    except IOError:
        font = ImageFont.load_default()

    # Calculate the width and height of the text to be added
    text_bbox = d.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calculate X, Y position of the text
    x = (width - text_width) // 2
    y = height - text_height - 10

    # Add text to image
    d.text((x, y), text, font=font, fill=(255, 255, 255))

    # Save the image to a file
    text_img_path = f'text_image_{text[:10]}.png'  # use a part of the text for unique naming
    img.save(text_img_path)
    return text_img_path

def create_video_from_images(images, voiceovers, output_path, captions, caption_array):
    final_clips = []
    
    for i, img in enumerate(images):
        try:       
            if i < len(voiceovers):
                audio_clip = mpy.AudioFileClip(voiceovers[i])
                image_clip = mpy.ImageClip(img['url']).set_duration(audio_clip.duration)
                
                if captions == "yesCaptions" and i < len(caption_array):
                    text_img_path = generate_text_image(caption_array[i], image_clip.w, 90, fontsize=50)
                    text_clip = mpy.ImageClip(text_img_path).set_duration(audio_clip.duration).set_position(('center', 'bottom'))
                    final_clip = mpy.CompositeVideoClip([image_clip, text_clip]).set_audio(audio_clip)
                else:
                    final_clip = image_clip.set_audio(audio_clip)
            else:
                image_clip = mpy.ImageClip(img['url']).set_duration(2)
                if captions == "yesCaptions" and i < len(caption_array):
                    text_img_path = generate_text_image(caption_array[i], image_clip.w, 90, fontsize=50)
                    text_clip = mpy.ImageClip(text_img_path).set_duration(2).set_position(('center', 'bottom'))
                    final_clip = mpy.CompositeVideoClip([image_clip, text_clip])
                else:
                    final_clip = image_clip
            
            final_clips.append(final_clip)
        except Exception as e:
            print(f"Error processing clip {i}: {e}")
    
    final_video = mpy.concatenate_videoclips(final_clips, method="compose")
    final_video.write_videofile(output_path, codec='libx264', fps=24)

    # Delete the audio files after creating the video
    for voiceover in voiceovers:
        os.remove(voiceover)

    return output_path

def generate_voiceover(sentence, index):
    prompt = sentence
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=prompt
    )

    audio_path = f"static/audio_{index}.mp3"
    response.stream_to_file(audio_path)
    
    # Verify the downloaded audio file duration
    audio_clip = mpy.AudioFileClip(audio_path)
    if audio_clip.duration == 0:
        raise ValueError(f"Downloaded audio file static/audio_{index}.mp3 has 0 duration.")
    
    return audio_path

@app.route('/')
def form():
    return render_template_string(form_html)

@app.route('/submit', methods=['POST'])
def submit():
    title = request.form['title']
    script = request.form['script']
    captions = request.form['captions']
    
    # Tokenize the script based on full stops
    tokenized_script = tokenize_by_full_stop(script)
    
    # Process each tokenized sentence and send to OpenAI API
    images = []
    voiceovers = []
    caption_array = []

    for index, sentence in enumerate(tokenized_script):
        prompt = generate_prompt_for_image(sentence)
        response = call_openai_api(prompt)
        image_url  = generate_image(response)
        images.append({'url': image_url, 'sentence': sentence})
        caption_array.append(sentence)

        # Generate voiceover
        voiceover = generate_voiceover(sentence, index)
        voiceovers.append(voiceover)
    
    # Ensure the static directory exists
    os.makedirs(os.path.join(app.root_path, 'static'), exist_ok=True)

    # Create a video from the generated images
    video_path = os.path.join('static', 'output_video.mp4')
    create_video_from_images(images, voiceovers, video_path, captions, caption_array)

    #Decrease the amount of left over vids and updata db
    
    # Redirect to output page with generated images and video
    return render_template('output.html', title=title, video_url=url_for('static_video', filename='output_video.mp4'), script=script, captions=captions)

# Custom route to serve video from the static directory
@app.route('/static_video/<path:filename>')
def static_video(filename):
    return send_from_directory('static', filename)

# Add this route to handle regeneration
@app.route('/regenerate', methods=['POST'])
def regenerate():
    title = request.form['title']
    script = request.form['script']
    captions = request.form['captions']
    
    # Tokenize the script based on full stops
    tokenized_script = tokenize_by_full_stop(script)
    
    # Process each tokenized sentence and send to OpenAI API
    images = []
    voiceovers = []
    caption_array = []

    for index, sentence in enumerate(tokenized_script):
        prompt = generate_prompt_for_image(sentence)
        response = call_openai_api(prompt)
        image_url = generate_image(response)
        images.append({'url': image_url, 'sentence': sentence})
        caption_array.append(sentence)

        # Generate voiceover
        voiceover = generate_voiceover(sentence, index)
        voiceovers.append(voiceover)
    
    # Ensure the static directory exists
    os.makedirs(os.path.join(app.root_path, 'static'), exist_ok=True)

    # Create a video from the generated images
    video_path = os.path.join('static', 'output_video.mp4')
    create_video_from_images(images, voiceovers, video_path, captions, caption_array)

    # Redirect to output page with generated images and video
    return render_template('output.html', title=title, video_url=url_for('static_video', filename='output_video.mp4'), script=script, captions=captions)

if __name__ == '__main__':
    app.run(debug=True)
