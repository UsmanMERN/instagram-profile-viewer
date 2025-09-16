# Instagram Profile Viewer: My Flask & Instagrapi Project

Hey there! I’m thrilled to share my **Instagram Profile Viewer**, a Flask-powered app I built to download Instagram stories, posts, reels, highlights, and profile details using the awesome **instagrapi** library. I poured my heart into creating a sleek, user-friendly UI/UX that’s responsive and intuitive, making it super easy to explore and download Instagram content. Whether you’re grabbing stories or diving into profile details, this app has it all! I’ve optimized it for serverless deployment on **Vercel** and included a **Dockerfile** for traditional hosting. With lazy loading, pagination, and robust error handling, everything runs smoothly. I’d love for you to check it out, star the repo, and maybe even contribute!

🌟 **Please star this repo** on [GitHub](https://github.com/UsmanMERN/instagram-profile-viewer) to show your support and help others find this project!  
🙌 **Contributors are welcome!** If you’re excited about this project, jump in—whether it’s fixing bugs, adding features, or improving the UI. Let’s make this even better together!
🚀 **More Tools Coming!** I’ve built tons of other cool tools like this one—think Snapchat downloaders, YouTube tools like YouTube converters, youtube downloader, and so much more. If this project gets some love, I’ll release those too, so show some support!

## What’s Cool About This Project?

- **Download All the Instagram Goodies**: Fetch stories, posts, reels, highlights, and profile details effortlessly.
- **Stunning UI/UX**: I crafted a modern, responsive interface that shines on desktops, tablets, and phones.
- **Lazy Loading Magic**: Media previews load first, with full content fetched on demand for a fast, efficient experience.
- **Pagination Done Right**: Seamlessly scroll through posts and reels with paginated API endpoints.
- **Smart Session Management**: Uses **instagrapi** to store login sessions in a `session.json` file, so you don’t need to log in repeatedly.
- **Timezone Support**: Converts timestamps to Asia/Kolkata timezone for a localized touch.
- **Serverless Ready**: Deploys effortlessly on Vercel with a custom `vercel.json` configuration.
- **Docker Support**: Includes a `Dockerfile` for containerized deployment on any server.
- **Error Handling**: Gracefully handles Instagram rate limits, invalid sessions, and private accounts.
- **Custom Number Formatting**: Added a Jinja2 filter to display follower counts in a readable format (e.g., 1.2M, 5.6K).
- **SEO-Friendly**: Packed with keywords to help folks find this project when searching for Instagram downloaders.

## Tech Stack I Used

- **Backend**: Flask (my favorite Python web framework)
- **Instagram API**: instagrapi (huge props to this amazing library!)
- **Frontend**: HTML, CSS, JavaScript (with a polished, responsive UI)
- **Deployment**: Vercel for serverless hosting, Docker for containerized setups
- **Dependencies**: Python 3.9+, requests, pytz, base64, Flask, instagrapi
- **Timezone Handling**: pytz for accurate timestamp conversions

## How to Get Started

### What You’ll Need

- **Python**: Version 3.9 or higher
- **pip**: Python package manager
- **Git**: To clone my repo
- **Vercel CLI**: For serverless deployment (optional)
- **Docker**: For containerized deployment (optional)

### Installation Steps

1. **Clone My Repo**
   ```bash
   git clone https://github.com/UsmanMERN/instagram-profile-viewer.git
   cd instagram-profile-viewer
   ```

2. **Set Up a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add Your Instagram Credentials**
   - Open `app.py` and plug in your Instagram username and password:
     ```python
     USERNAME = "your_instagram_username_here"
     PASSWORD = "your_instagram_password_here"
     SESSION_FILE = "session.json"
     ```
   - **Pro Tip**: Keep your credentials secure! Never commit them to a public repo.

5. **Run the App Locally**
   ```bash
   python app.py
   ```
   - The app will be live at `http://localhost:8080`.

6. **Check Out the UI**
   - Open `http://localhost:8080` in your browser and explore the sleek interface I built!

### Dependencies

Here’s what you need in your `requirements.txt`:
```
Flask==2.0.1
instagrapi==1.16.35
requests==2.28.1
pytz==2023.3
```

Install them with:
```bash
pip install -r requirements.txt
```

## Deploying the App

### Vercel (Serverless Hosting)

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Set Up `vercel.json`**
   I’ve included a `vercel.json` file for seamless serverless deployment:
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "app.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "app.py"
       }
     ]
   }
   ```

3. **Deploy to Vercel**
   ```bash
   vercel
   ```
   - Follow the prompts to deploy.
   - Set environment variables (`USERNAME`, `PASSWORD`, `SESSION_FILE`) in the Vercel dashboard.

4. **Access Your App**
   - Vercel will provide a URL (e.g., `https://your-app-name.vercel.app`) to access the app.

### Docker (Containerized Hosting)

1. **Create a `Dockerfile`**
   I’ve added a `Dockerfile` for containerized deployment:
   ```dockerfile
   # Use official Python image
   FROM python:3.9-slim

   # Set working directory
   WORKDIR /app

   # Copy requirements and install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY . .

   # Expose port
   EXPOSE 8080

   # Command to run the application
   CMD ["python", "app.py"]
   ```

2. **Build and Run the Docker Container**
   ```bash
   docker build -t instagram-profile-viewer .
   docker run -p 8080:8080 -e USERNAME=your_username -e PASSWORD=your_password instagram-profile-viewer
   ```

3. **Access the App**
   - Head to `http://localhost:8080` in your browser.

## How to Use It

1. **Home Page**: Visit the root URL (`/`) to see my awesome UI, starting with the "Stories" tab.
2. **Download Stories**: Enter an Instagram username to fetch stories, complete with previews and viewer details (for your own stories).
3. **Download Posts/Reels**: Paste a post or reel URL to grab media and metadata like likes, comments, and captions.
4. **View Highlights**: Check out highlight metadata and load individual items on demand.
5. **Profile Details**: Get rich profile info, including followers, following, bio, and profile picture.
6. **Lazy Loading**: Media loads only when needed via the `/download_media_content` endpoint—super efficient!
7. **Pagination**: Use `/get_posts` and `/get_reels` to fetch more content with smooth pagination.

## API Endpoints I Built

- **GET /**: Loads the main UI with the "Stories" tab active.
- **GET /profile?username=<username>**: Fetches profile details for a given username.
- **GET /stories?username=<username>&user_id=<user_id>**: Grabs stories for a user.
- **POST /download_story**: Downloads stories and profile details for a username.
- **POST /download_post**: Downloads a post or reel by URL.
- **GET /get_posts?username=<username>&user_id=<user_id>&max_id=<end_cursor>**: Gets paginated posts.
- **GET /get_reels?username=<username>&user_id=<user_id>&max_id=<end_cursor>**: Gets paginated reels.
- **GET /get_highlights?username=<username>&user_id=<user_id>**: Retrieves highlight metadata.
- **GET /get_highlight_items?username=<username>&user_id=<user_id>&highlight_id=<highlight_id>**: Fetches items for a specific highlight.
- **POST /download_media_content**: Downloads media content on demand for lazy loading.

## The UI/UX I’m Proud Of

- **Responsive Design**: Looks fantastic on any device—desktop, tablet, or phone.
- **Smooth Navigation**: Tabs for stories, posts, reels, and highlights with clear, intuitive controls.
- **Media Previews**: Shows base64-encoded previews for stories, posts, reels, and highlights to keep things snappy.
- **Interactive Goodies**: Pagination and on-demand loading make browsing a joy.
- **User-Friendly Errors**: Clear messages for invalid inputs, private accounts, or API hiccups.
- **Profile Display**: Shows off profile details with formatted follower counts and clickable external links.

## 🙌 Contribute to the Project!

I’d love to see this project grow with contributions from the community! Whether you’re fixing bugs, adding new features, improving the UI, or optimizing performance, your input is super welcome. Check out the [GitHub repo](https://github.com/UsmanMERN/instagram-profile-viewer) to get started. Here’s how you can contribute:

1. Fork the repo.
2. Create a new branch (`git checkout -b feature/awesome-feature`).
3. Make your changes and commit them (`git commit -m 'Add awesome feature'`).
4. Push to your branch (`git push origin feature/awesome-feature`).
5. Open a pull request and let’s chat about your ideas!

Feel free to open issues for bugs, feature requests, or just to share feedback. Let’s make this project even more awesome together!

## 🌟 Show Some Love!

If you find this project useful or just think it’s cool, please give it a **star** on [GitHub](https://github.com/UsmanMERN/instagram-profile-viewer)! It helps others discover the project and keeps me motivated to keep improving it. Share it with friends, tweet about it, or drop a comment in the issues section—I’d love to hear what you think!

## 🙏 Credits

This project relies heavily on the fantastic work of the **instagrapi** library. A huge thank you to the developers and contributors of instagrapi for providing a powerful and reliable Instagram Private API wrapper.  
- **instagrapi**: [https://github.com/subzeroid/instagrapi](https://github.com/subzeroid/instagrapi)

I also want to give a shoutout to:
- **Flask**: For being an awesome, lightweight web framework.
- **Vercel**: For making serverless deployment a breeze.
- **Docker**: For enabling easy containerized hosting.

## ⚠️ Disclaimer

This application is for **educational purposes only**. It is not affiliated with, endorsed by, or in any way officially connected with Instagram or any of its subsidiaries or affiliates. Be responsible and respect the privacy and content of others.

## Notes

- **Rate Limits**: I added delays (`time.sleep` and `delay_range`) to respect Instagram’s rate limits and avoid bot detection.
- **Private Accounts**: Some features (like stories or posts) may be limited for private accounts unless you follow them.
- **Session Management**: The `session.json` file keeps your login session safe. Don’t expose it in public deployments!
- **Security**: Store your Instagram credentials securely (e.g., as environment variables) and avoid hardcoding them in production.

## Keywords

Instagram downloader, Instagram profile viewer, Flask instagrapi, Instagram stories downloader, Instagram reels downloader, Instagram posts downloader, Instagram highlights downloader, social media scraper, Flask API, serverless deployment, Vercel Flask app, Docker Python app, Instagram profile details, lazy loading media, responsive UI/UX, social media automation, Python web app.

## License

This project is licensed under the MIT License. Check out the [LICENSE](LICENSE) file for details.

