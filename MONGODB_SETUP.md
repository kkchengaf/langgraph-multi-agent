# MongoDB Installation Guide for Windows

This guide covers installing MongoDB Community Server on Windows 11.

---

## Step 1: Download MongoDB Community Server

1. Visit: https://www.mongodb.com/try/download/community
2. Select:
   - **Version:** 8.0 (or latest)
   - **Package:** MSI
   - **Platform:** Windows
3. Click **Download**

---

## Step 2: Install MongoDB

1. Run the downloaded `.msi` file
2. Choose **Complete** installation type
3. **Important:** Uncheck "Install MongoDB Compass" (optional, can install later)
4. Click **Install**
5. Wait for installation to complete

---

## Step 3: Create Data Directory

MongoDB requires a data directory. Create it:

1. Open **Command Prompt** (cmd) as Administrator
2. Run:
```cmd
mkdir E:\mongodb\db
```

---

## Step 4: Start MongoDB Service

### Option A: Run as Service (Recommended)

1. Open **Command Prompt** as Administrator
2. Run:
```cmd
"C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe" --install --serviceName MongoDB --serviceDisplayName MongoDB --dbpath E:\mongodb\db
```

3. Start the service:
```cmd
net start MongoDB
```

### Option B: Run Manually (For Development)

1. Open a terminal
2. Run:
```cmd
"C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe" --dbpath E:\mongodb\db
```

Keep this terminal open while using MongoDB.

---

## Step 5: Verify Installation

1. Open a new terminal
2. Run the MongoDB shell:
```cmd
"C:\Program Files\MongoDB\Server\8.0\bin\mongosh.exe"
```

3. You should see:
```
Connecting to: mongodb://127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000
...
mongosh>
```

4. Type `exit` to quit

---

## Step 6: Add MongoDB to PATH (Optional)

To run `mongod` and `mongosh` from any directory:

1. Press **Win + R**, type `sysdm.cpl`, press Enter
2. Go to **Advanced** > **Environment Variables**
3. Under **User variables**, find **Path**, click **Edit**
4. Click **New** and add:
```
C:\Program Files\MongoDB\Server\8.0\bin
```
5. Click **OK** to save

---

## Step 7: Install PyMongo

Update your Python dependencies:

```cmd
pip install pymongo
```

---

## Configuration for Your App

Your app will connect to MongoDB using:

```
mongodb://localhost:27017/
```

Database name: `langgraph_chat`

---

## Troubleshooting

### MongoDB won't start
- Make sure no other process is using port 27017
- Check if the data directory exists
- Run `mongod` manually to see error messages

### Service already exists
```
net stop MongoDB
"C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe" --remove
```
Then reinstall the service.

### Permission denied
- Run Command Prompt as Administrator

---

## Optional: Install MongoDB Compass (GUI)

1. Download from: https://www.mongodb.com/products/compass
2. Run the installer
3. Connect to: `mongodb://localhost:27017`

---

## Quick Commands Reference

| Command | Description |
|---------|-------------|
| `net start MongoDB` | Start MongoDB service |
| `net stop MongoDB` | Stop MongoDB service |
| `mongosh` | Open MongoDB shell |
| `mongod --dbpath E:\mongodb\db` | Run MongoDB manually |

---

After installation, the backend API will be able to connect to MongoDB and store chat threads.
