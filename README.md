# IRON-FILTER-BOT

<div align="center">
   <img src="https://img.shields.io/github/repo-size/IronmanHUB4VF/IRON-FILTER-BOT?color=green&label=Repo%20Size&labelColor=292c3b" alt="Repo Size">
   <img src="https://img.shields.io/badge/Version-1.0-brightgreen.svg" alt="Version">
   <img src="https://img.shields.io/badge/Build-Docker-blue" alt="Build">
   <img src="https://img.shields.io/github/languages/count/IronmanHUB4VF/IRON-FILTER-BOT?style=flat&label=Total%20Languages&labelColor=292c3b&color=blueviolet" alt="Languages">
   <img src="https://img.shields.io/github/languages/top/IronmanHUB4VF/IRON-FILTER-BOT?style=flat&logo=python&labelColor=292c3b" alt="Python">
   
   <img src="https://img.shields.io/github/commit-activity/m/IronmanHUB4VF/IRON-FILTER-BOT?logo=github&labelColor=292c3b&label=Github%20Commits" alt="Github Commits">
   <img src="https://img.shields.io/badge/Platform-Every-orange" alt="Platform">
   <img src="https://img.shields.io/github/forks/IronmanHUB4VF/IRON-FILTER-BOT?style=flat&logo=github&label=Forks&labelColor=292c3b&color=critical" alt="Forks">
   <img src="https://img.shields.io/github/stars/IronmanHUB4VF/IRON-FILTER-BOT?style=flat&logo=github&label=Stars&labelColor=292c3b&color=yellow" alt="Stars">
   <img src="https://img.shields.io/github/issues-pr-raw/IronmanHUB4VF/IRON-FILTER-BOT?style=flat&label=Open%20Pull%20Requests&labelColor=292c3b" alt="Pull Requests">
</div>

## 🚀 Deployment Guide

<details>
<summary><strong>🌐 Koyeb Deployment</strong></summary>

1. **🔗 Link Your Repository**: Connect your GitHub repository to Koyeb.
   - Navigate to your Koyeb dashboard.
   - Click on "Create Application" and choose "GitHub" as the source.
   - Select the `IRON-FILTER-BOT` repository.
2. **⚙️ Buildpack Selection**:
   - In the application settings, select `Dockerfile` as the buildpack.
   
3. **🔒 Environment Variables**:
   - If you haven’t added the `config.env` file to the repository, configure the necessary environment variables directly in Koyeb.
     - Go to the "Settings" tab, and under "Environment Variables," add the required variables (e.g., `TELEGRAM_API`, `TELEGRAM_HASH`, `BOT_TOKEN`).
     - **Variable Descriptions**:
        | Variable | Required | Description |
        |----------|----------|-------------|
        | `BOT_TOKEN` | ✅ | Telegram bot token from [@BotFather](https://t.me/BotFather) |
        | `TELEGRAM_HASH` | ✅ | Telegram API hash from [my.telegram.org](https://my.telegram.org) |
        | `LOG_CHANNEL` | ✅ | Channel ID for bot logs (start with `-100`) |
        | `DATABASE_CHANNEL` | ✅ | Channel ID for database storage |
        | `DATABASE_URL` | ✅ | MongoDB connection URL |
        | `FILES_DATABASE_URL` | ✅ | MongoDB connection URL for files |
        | `OWNER_ID` | ✅ | Your Telegram user ID |
        | `BOT_BASE_URL` | ✅ | Required only for webhook configuration |
        | `PORT` | ✅ | port for web server (default: 8080) |
4. **🌐 Exposed Ports**:
   - Set the `PORT` number to your desired value (recommended: `8080`).
5. **💾 Save and Deploy**:
   - Save the configuration.
   - Click on "Deploy" to initiate the build and deployment process.
6. **📊 Monitor Deployment**:
   - Check the "Logs" section to ensure the application is running without issues.

</details>

<details>
<summary><strong>🖥️ VPS Deployment</strong></summary>

1. **📂 Clone the Repository**:
   - Clone the repository to your local machine:
      ```bash
      git clone https://github.com/Ironman966232/IRON-FILTER-BOT.git
      ```
2. **📁 Navigate to Project Directory**:
   - Change to the project directory:
      ```bash
      cd IRON-FILTER-BOT
      ```
3. **🛠️ Add Configuration**:
   - Add the `config.env` file with your bot's credentials and settings to the root directory.
   - **Variable Descriptions**:
        | Variable | Required | Description |
        |----------|----------|-------------|
        | `BOT_TOKEN` | ✅ | Telegram bot token from [@BotFather](https://t.me/BotFather) |
        | `TELEGRAM_HASH` | ✅ | Telegram API hash from [my.telegram.org](https://my.telegram.org) |
        | `LOG_CHANNEL` | ✅ | Channel ID for bot logs (start with `-100`) |
        | `DATABASE_CHANNEL` | ✅ | Channel ID for database storage |
        | `DATABASE_URL` | ✅ | MongoDB connection URL |
        | `FILES_DATABASE_URL` | ✅ | MongoDB connection URL for files |
        | `OWNER_ID` | ✅ | Your Telegram user ID |
        | `BOT_BASE_URL` | ✅ | Required only for webhook configuration |
        | `PORT` | ✅ | port for web server (default: 8080) |
4. **🌐 Set Port**:
   - Update the `Dockerfile` to change the `PORT` if needed (default: `8080`).
5. **⬆️ Update System Packages**:
   ```bash
   sudo apt update
   ```
6. **🐍 Install Python**:
   ```bash
   sudo apt install python3 python3-pip
   ```
7. **🐋 Install Docker**:
   - Follow the [official Docker installation guide](https://docs.docker.com/engine/install/) or use the convenience script:
      ```bash
      curl -fsSL https://get.docker.com | bash
      ```
8. **Check Docker Work Or Not**
   ```bash
   docker --version
   ```
   - If Docker is installed, you'll see the version information.

   ```bash
   docker run hello-world
   ```
   - If successful, you'll see a message indicating the container has run and exited successfully.
9. **⚙️ Build Docker Image**:
   - Build the Docker image from the current directory:
      ```bash
      sudo docker build . -t ironfilter
      ```
10. **🚀 Run Docker Container**:
   - Run the Docker container with the specified port (8080 in this example):
      ```bash
      sudo docker run -p 8080:8080 ironfilter
      ```
11. **📊 Monitor Container**:
   - View logs to ensure the bot is running:
      ```bash
      sudo docker logs -f ironfilter
      ```

#### 🛑 Stopping Docker

1. **🔍 List Running Containers**:
   ```bash
   sudo docker ps
   ```
2. **🛑 Stop Container**:
   ```bash
   sudo docker stop <container-id>
   ```

3. **❌ Remove Container** (optional):
   ```bash
   sudo docker rm <container-id>
   ```
4. **❌ Remove Not Running Containers (including exited, created, or dead containers)**:
   ```bash
   sudo docker rm $(docker ps -aq --filter "status=exited" --filter "status=created" --filter "status=dead")
   ```


</details>

### 🎯 Features

<details>
<summary><strong>✨ Features</strong></summary>

- **🔒 File Security**: Securely manage files and protect them from unauthorized access.
- **📊 Analytics**: Track file usage and access patterns to optimize storage and improve user experience.
- **📂 File Indexing**: Index files from channels and messages, allowing users to easily access and manage their files.
- **💬 User Commands**: A user-friendly command interface for easy interaction with the bot.
- **🔐 Access Control**: Users must register to gain access to certain functionalities, ensuring secure usage.
- **⚡ Dynamic Responses**: The bot responds with inline buttons for various actions, enhancing user experience.
- **📈 Status Updates**: Provides users with current statistics about the bot's operations.
- **🔍 Filtering Options**: Users can filter files based on quality, language, season, year, and episode.
- **⚙️ Bot Settings**: Configurable options for bot behavior and functionality.
- **🔧 User Settings**: Customizable settings for individual users, including language and quality preferences.
</details>



### 📜 Commands

<details>
<summary><strong>🛠️ Commands</strong></summary>

- **/start**: Initializes the bot and provides access to its features. Users must register to use the bot.
- **/id**: To get user and chat id.
- **/stickerid**: To get sticker id.
- **/us**: Open User Settings.
- **/media_info**: Get Media info like audios, quality, subtitles, codec.
- **/minfo_json**: To get file information from telegram json.
- **/chats_list**: [ADMIN] To get all chats list where bot connected.
- **/checkrights <chat_id> [user_id]**: [ADMIN] To know the rights of the chat or users in the chat.
- **/stats**: [ADMIN] Check mongodb database stats.
- **/index**: Starts the indexing process for files in a channel.
- **/bstats**: [ADMIN] Check Bot & System stats.
- **/ping**: [ADMIN] check between server to bot connection speed.
- **/help**: Get detailed help.
- **/deletefile**: [ADMIN] for delete single file in mongodb.
- **/deletefiles**: [ADMIN] for delete multiple file in mongodb.
- **/delpmuser <user_id>**: [ADMIN] for delete specific PM user from mongodb.
- **/delfsubuser <user_id>**: [ADMIN] for delete specific Fsub user from mongodb.
- **/setskip <link1> <link2>**: [ADMIN] for skip files to index
- **/authorize**: [ADMIN] To authorize user.
- **/unauthorize**: [ADMIN] To unauthorize user.
- **/addsudo**: [ADMIN] To promote user to sudo user.
- **/rmsudo**: [ADMIN] To demote sudo user to user.
- **/bs**: [ADMIN] Open Bot settings.
- **/broadcast**: [ADMIN] Broadcast message to all users.
- **/log**: [ADMIN] View log.
- **/showskip**: [ADMIN] Displays the current skip IDs.
- **/restart**: [ADMIN] Restart the bot
</details>

## More Info About Features
<details>
- <summary><strong>📂 Indexing Options</strong></summary>

- The IRON-FILTER-BOT supports two indexing formats, giving you flexibility in how files are listed:

- **Up-to-Down:**

- Files are indexed in ascending order, starting from the oldest message to the newest.
- Ideal for maintaining a chronological order of files.

- **Down-to-Up:**

- Files are indexed in descending order, starting from the newest message to the oldest.
- Perfect for prioritizing recently added files.

- You can choose the desired format during the indexing process to suit your needs.
  
- **For more details [Click Here](https://justpaste.it/44h6r)**
</details>

<details>
<summary><strong>⚙️ **User Settings**</strong></summary>

🌍 **Language**
- Choose your preferred language for the bot’s responses. Available options include languages like English, Hindi, Telugu, and more!
- You can set or update your language anytime. If you want to reset to default, simply use the reset option.

🎥 **Quality**
- Set your preferred video quality (e.g., 360p, 720p, 1080p). This setting ensures that the content delivered to you matches your preferred quality.

📂 **File Type**
- Choose what type of files you want to receive (Video, Audio, or Document). Whether you're looking for multimedia files or documents, this setting ensures you get the right format.

🍿 **IMDB Integration**
- Turn IMDB results on or off based on your preference. When enabled, you will receive IMDB-related information alongside content.

**How to Access User Settings**:
1. Tap on any of the available settings options (Language, Quality, etc.).
2. Choose your desired value or reset to the default.
3. Use the 'Back' button to go to the previous menu or 'Close' to exit the settings menu.

---

💡 **How It Works**

- **User Settings** are stored and managed per user, meaning you can personalize your settings.
- Changes to your settings take effect immediately.
- You can also **reset** all settings or specific ones like language and quality at any time.
- The bot uses **pagination** to make it easy for you to browse through options (like a long list of languages or qualities).

- **For More Details [Click Here](https://justpaste.it/es4l2)**
---
</details>

<details>
<summary><strong>🛠 **Bot Settings**</strong></summary>

- **Bot settings** are the configuration controls for how the bot behaves and interacts with users.
- These settings are managed by the bot administrator and sudo users and can include settings for the bot's responses, command prefixes, and system behaviors.
- These can be accessed by the bot administrator and can include settings for the bot's responses, command prefixes, and system behaviors.
- Users will not need to modify these settings, but the bot admin can tweak them for better performance.

- **For More Details [Click Here](https://justpaste.it/auizk)**
---
</details>

## 🔗 Support

- **💬 Telegram Support Group**: [Join Now](https://t.me/movie_and_series_hub4vf)
- **📣 Telegram Channel**: [Follow Updates](https://t.me/BOT_UPDATE_HUB4VF)
