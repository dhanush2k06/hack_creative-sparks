import os
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
from pymongo import MongoClient

# MongoDB setup
client = MongoClient("mongodb://localhost:27017")
db1 = client["ai"]["repos"]         # repo_id, name, url
db2 = client["ai"]["repo_files"]    # repo_id, file_name, env, port, frameworks

def fetch_repos(username):
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else []

def clone_repo(clone_url, name):
    path = f"./tmp/{name}"
    if os.path.exists(path): shutil.rmtree(path)
    subprocess.run(["git", "clone", clone_url, path], check=True)
    return path

def extract_env_ports_frameworks(filepath):
    env_vars = []
    ports = []
    frameworks = []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            content = ''.join(lines).lower()
            for line in lines:
                if '=' in line and not line.strip().startswith("#"):
                    env_vars.append(line.strip())
                if 'port' in line.lower() and any(char.isdigit() for char in line):
                    ports.append(line.strip())

            # Check for frameworks
            if "flask" in content:
                frameworks.append("Flask")
            if "django" in content:
                frameworks.append("Django")
            if "express" in content:
                frameworks.append("Express.js")
            if "react" in content:
                frameworks.append("React")
            if "spring" in content:
                frameworks.append("Spring")
    except:
        pass

    return env_vars, ports, list(set(frameworks))

def analyze_repo(repo_name, repo_url, repo_id, output_callback):
    path = clone_repo(repo_url, repo_name)

    for root, _, files in os.walk(path):
        for file in files:
            if not file.endswith(('.py', '.env', '.js', '.yml', '.yaml', '.json', '.txt')): continue
            full_path = os.path.join(root, file)
            env, port, frameworks = extract_env_ports_frameworks(full_path)

            db2.insert_one({
                "repo_id": repo_id,
                "file_name": os.path.relpath(full_path, path),
                "env": env,
                "port": port,
                "frameworks": frameworks
            })
            output_callback(f"✔️ {file} stored: Env={len(env)}, Port={len(port)}, Frameworks={frameworks}")

    shutil.rmtree(path)

def run_analysis(username, output_callback):
    repos = fetch_repos(username)
    output_callback(f"🔍 Found {len(repos)} repos")

    for repo in repos:
        repo_id = repo["id"]
        repo_name = repo["name"]
        repo_url = repo["clone_url"]
        db1.insert_one({
            "repo_id": repo_id,
            "repo_name": repo_name,
            "repo_url": repo["html_url"]
        })
        output_callback(f"\n📦 Analyzing: {repo_name}")
        try:
            analyze_repo(repo_name, repo_url, repo_id, output_callback)
        except Exception as e:
            output_callback(f"❌ {repo_name}: {e}")

# --- UI ---
class RepoAnalyzerApp:
    def __init__(self, root):
        self.root = root
        root.title("GitHub Repo Analyzer")
        root.geometry("900x600")

        tk.Label(root, text="GitHub Username:", font=("Arial", 12)).pack(pady=5)
        self.user_entry = tk.Entry(root, width=50, font=("Arial", 12))
        self.user_entry.pack(pady=5)

        tk.Button(root, text="Start", command=self.start_analysis, font=("Arial", 12)).pack(pady=10)

        self.output = scrolledtext.ScrolledText(root, width=110, height=30, font=("Courier", 10))
        self.output.pack(padx=10, pady=10)

    def log(self, msg):
        self.output.insert(tk.END, msg + "\n")
        self.output.see(tk.END)

    def start_analysis(self):
        username = self.user_entry.get().strip()
        if not username:
            messagebox.showwarning("Input needed", "Enter GitHub username.")
            return
        self.output.delete(1.0, tk.END)
        self.log("🚀 Starting analysis...")
        self.root.after(100, lambda: run_analysis(username, self.log))


if __name__ == "__main__":
    root = tk.Tk()
    app = RepoAnalyzerApp(root)
    root.mainloop()
    