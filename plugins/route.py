from aiohttp import web
from database.database import db
from config import OWNER
import secrets
import aiohttp
import asyncio
from datetime import datetime, timedelta

routes = web.RouteTableDef()

async def resolve_shortlink(shortlink_url):
    """
    Follow the shortlink and get the final destination URL
    without exposing the shortlink to the user
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(shortlink_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as response:
                # Return the final URL after all redirects
                return str(response.url)
    except Exception as e:
        print(f"Error resolving shortlink: {e}")
        # Return the original shortlink if resolution fails
        return shortlink_url

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Movies8777 FileStore")

@routes.get("/redirect", allow_head=True)
async def redirect_handler(request):
    """
    Handle redirect: resolve shortlink on server to get final destination,
    then redirect user directly to it (shortlink never exposed to user)
    """
    redirect_id = request.query.get('id')
    
    if not redirect_id:
        return web.Response(
            text="<html><body><h1>Invalid Request</h1><p>Missing redirect ID.</p></body></html>",
            content_type='text/html',
            status=400
        )
    
    try:
        # Get full redirect data from database
        redirect_data = await db.get_redirect_full(redirect_id)
        
        if not redirect_data or not redirect_data.get('shortlink'):
            return web.Response(
                text="<html><body><h1>Link Expired</h1><p>This redirect link has expired. Please request a new one from the bot.</p></body></html>",
                content_type='text/html',
                status=404
            )
        
        shortlink = redirect_data['shortlink']
        user_id = redirect_data.get('user_id')
        created_at = redirect_data.get('created_at')
        
        # Check if user is actually verified
        is_user_verified = False
        if user_id:
            verify_status = await db.get_verify_status(user_id)
            is_user_verified = verify_status.get('is_verified', False) if verify_status else False
        
        # If user is not verified, check if link has expired (2 minutes)
        if not is_user_verified and created_at:
            # Check if more than 2 minutes have passed
            link_age = datetime.now() - created_at
            if link_age > timedelta(minutes=2):
                # Link has expired
                return web.Response(
                    text="<html><body><h1>Link Expired</h1><p>This verification link has expired. Please request a new one from the bot.</p></body></html>",
                    content_type='text/html',
                    status=404
                )
        
        if is_user_verified:
            # User already verified - show verification message instead of redirecting
            verification_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Verified - Movies8777 FileStore</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            height: 100vh;
            background: linear-gradient(135deg, #000 0%, #1a0033 100%);
            font-family: 'Segoe UI', Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
        }
        
        .card {
            position: relative;
            background: rgba(10, 10, 10, 0.85);
            border-radius: 20px;
            padding: 60px 80px;
            text-align: center;
            box-shadow:
                0 0 30px rgba(0, 255, 100, 0.3),
                0 0 60px rgba(0, 255, 100, 0.15);
            border: 2px solid rgba(0, 255, 100, 0.3);
            backdrop-filter: blur(10px);
            max-width: 500px;
        }
        
        .checkmark {
            width: 80px;
            height: 80px;
            margin: 0 auto 25px;
            border: 3px solid #00ff64;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 20px rgba(0, 255, 100, 0.6);
            animation: scaleIn 0.6s ease-out;
        }
        
        .checkmark::after {
            content: "✓";
            font-size: 50px;
            color: #00ff64;
            font-weight: bold;
        }
        
        h1 {
            font-size: 28px;
            margin-bottom: 12px;
            color: #00ff64;
            text-shadow: 0 0 15px rgba(0, 255, 100, 0.7);
        }
        
        .subtitle {
            font-size: 16px;
            color: #00ffcc;
            margin-bottom: 8px;
            text-shadow: 0 0 8px rgba(0, 255, 255, 0.5);
        }
        
        p {
            font-size: 15px;
            color: #ccc;
            line-height: 1.6;
            margin-top: 15px;
        }
        
        .button {
            display: inline-block;
            margin-top: 30px;
            padding: 12px 35px;
            background: linear-gradient(135deg, #00ff64, #00ffcc);
            color: #000;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 0 20px rgba(0, 255, 100, 0.4);
        }
        
        .button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 30px rgba(0, 255, 100, 0.6);
        }
        
        @keyframes scaleIn {
            from {
                transform: scale(0);
                opacity: 0;
            }
            to {
                transform: scale(1);
                opacity: 1;
            }
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="checkmark"></div>
        <h1>You are Verified!</h1>
        <div class="subtitle">Status: Active</div>
        <p>You have already verified your access. You can continue using the bot for all your file-sharing needs.</p>
        <button class="button" onclick="window.location.href='https://t.me/Spicylinebun'">Back to Bot</button>
    </div>
</body>
</html>
            """
            return web.Response(text=verification_html, content_type='text/html')
        
        # Resolve shortlink on server side to get final destination
        # This follows all redirects and returns the actual destination URL
        final_destination = await resolve_shortlink(shortlink)
        
        # Return loading page that will redirect user to final destination
        # The shortlink is never exposed to the browser
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Redirecting...</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        height: 100vh;
        overflow: hidden;
        background: #000;
        font-family: 'Segoe UI', Arial, sans-serif;
        display: flex;
        justify-content: center;
        align-items: center;
        color: #fff;
    }

    /* Neon glow container */
    .card {
        position: relative;
        z-index: 2;
        background: rgba(10, 10, 10, 0.75);
        border-radius: 16px;
        padding: 45px 55px;
        text-align: center;
        box-shadow:
            0 0 20px rgba(0, 255, 255, 0.25),
            0 0 40px rgba(0, 255, 255, 0.15);
        border: 1px solid rgba(0, 255, 255, 0.25);
        backdrop-filter: blur(10px);
    }

    .card h1 {
        font-size: 24px;
        margin-bottom: 8px;
        color: #00ffff;
        text-shadow: 0 0 10px rgba(0,255,255,0.8);
    }

    .card p {
        font-size: 14px;
        opacity: 0.85;
        margin-bottom: 20px;
    }

    /* Progress bar */
    .progress-container {
        width: 100%;
        height: 8px;
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        overflow: hidden;
        margin-top: 10px;
    }

    .progress-bar {
        width: 0%;
        height: 100%;
        background: linear-gradient(90deg, #00ffff, #00ff88);
        box-shadow: 0 0 12px #00ffff;
        transition: width 0.1s linear;
    }

    .percent {
        margin-top: 12px;
        font-size: 13px;
        letter-spacing: 1px;
        color: #00ffea;
        text-shadow: 0 0 8px rgba(0,255,255,0.7);
    }

    /* Rain animation */
    .rain {
        position: absolute;
        inset: 0;
        overflow: hidden;
        z-index: 1;
    }

    .square {
        position: absolute;
        top: -40px;
        width: 14px;
        height: 14px;
        background: rgba(0, 255, 255, 0.8);
        box-shadow: 0 0 12px rgba(0,255,255,0.8);
        animation: fall linear infinite;
        border-radius: 2px;
    }

    @keyframes fall {
        to {
            transform: translateY(110vh) rotate(360deg);
            opacity: 0;
        }
    }
</style>
</head>

<body>

<!-- Neon rain -->
<div class="rain" id="rain"></div>

<!-- Center card -->
<div class="card">
    <h1>Accessing Link</h1>
    <p>Preparing secure redirect</p>

    <div class="progress-container">
        <div class="progress-bar" id="progressBar"></div>
    </div>

    <div class="percent" id="percent">0%</div>
</div>

<script>
    // Mark this redirect as visited when page loads
    fetch('/mark-visited?id=%REDIRECT_ID%', {method: 'GET'}).catch(e => console.log('Visited marked'));

    // Neon rain squares
    const rain = document.getElementById("rain");
    for (let i = 0; i < 60; i++) {
        const sq = document.createElement("div");
        sq.className = "square";
        sq.style.left = Math.random() * 100 + "vw";
        sq.style.animationDuration = (Math.random() * 3 + 2) + "s";
        sq.style.animationDelay = Math.random() * 5 + "s";
        sq.style.opacity = Math.random();
        sq.style.transform = `scale(${Math.random() + 0.4})`;
        rain.appendChild(sq);
    }

    // Progress logic
    let progress = 0;
    const bar = document.getElementById("progressBar");
    const percent = document.getElementById("percent");

    const interval = setInterval(() => {
        progress += Math.floor(Math.random() * 4) + 1;
        if (progress >= 100) {
            progress = 100;
            clearInterval(interval);

            setTimeout(() => {
                window.location.replace("%FINAL_DESTINATION%");
            }, 400);
        }

        bar.style.width = progress + "%";
        percent.textContent = progress + "%";
    }, 60);
</script>

</body>
</html>
        """
        
        # Replace placeholder with actual destination URL
        html_content = html_content.replace("%FINAL_DESTINATION%", final_destination)
        html_content = html_content.replace("%REDIRECT_ID%", redirect_id)
        
        return web.Response(text=html_content, content_type='text/html')
        
    except Exception as e:
        return web.Response(
            text=f"<html><body><h1>Error</h1><p>An error occurred: {str(e)}</p></body></html>",
            content_type='text/html',
            status=500
        )

@routes.get("/mark-visited", allow_head=True)
async def mark_visited_handler(request):
    """Mark a redirect as visited"""
    redirect_id = request.query.get('id')
    
    if redirect_id:
        try:
            await db.mark_redirect_visited(redirect_id)
            return web.json_response({'status': 'success'})
        except Exception as e:
            print(f"Error marking redirect visited: {e}")
            return web.json_response({'status': 'error'})
    
    return web.json_response({'status': 'invalid'})

@routes.get("/verify", allow_head=True)
async def verify_redirect_handler(request):
    user_id = request.query.get('user_id')
    token = request.query.get('token')
    
    if not user_id or not token:
        return web.Response(
            text="<html><body><h1>Invalid Request</h1><p>Missing parameters. Please request again from the bot.</p></body></html>",
            content_type='text/html',
            status=400
        )
    
    try:
        # Get verification data from database
        user_id = int(user_id)
        verify_status = await db.get_verify_status(user_id)
        
        if not verify_status or verify_status.get('verify_token') != token or not verify_status.get('link'):
            return web.Response(
                text="<html><body><h1>Invalid or Expired Link</h1><p>Token not found or expired. Please request again from the bot.</p></body></html>",
                content_type='text/html',
                status=404
            )
        
        shortlink = verify_status['link']
        
        # HTML page that displays message and redirects to shortener
        html_content = f"""
        <html>
        <head>
            <title>Verify - Movies8777 FileStore</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 500px;
                }}
                h1 {{
                    color: #333;
                    margin-top: 0;
                }}
                p {{
                    color: #666;
                    line-height: 1.6;
                }}
                .button {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                    font-weight: bold;
                    transition: background 0.3s;
                }}
                .button:hover {{
                    background: #764ba2;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Verify Your Access</h1>
                <p>Click the button below to complete verification.</p>
                <p>After verification, you'll be able to access your files.</p>
                <a href="{shortlink}" class="button">Verify Now</a>
                <p style="font-size: 12px; margin-top: 30px; color: #999;">If the button doesn't work, <a href="{shortlink}">click here</a></p>
            </div>
        </body>
        </html>
        """
        
        return web.Response(text=html_content, content_type='text/html')
        
    except Exception as e:
        return web.Response(
            text=f"<html><body><h1>Error</h1><p>An error occurred: {str(e)}</p></body></html>",
            content_type='text/html',
            status=500
        )
