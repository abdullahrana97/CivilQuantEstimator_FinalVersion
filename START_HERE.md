# Start here: run, upload and deploy

Keep your previous Civil QuantEstimate folder as a backup. Extract this ZIP into a **new** folder named `civil-quantestimate-v2`. Do not mix the old `utils` files into this version: its modules live in `core` and `ai`.

## 1. Open the correct folder

Open the extracted folder in VS Code: **File -> Open Folder**. You should see `app.py`, `requirements.txt` and `constraints.txt` directly inside it.

Choose **Terminal -> New Terminal**. On Windows, choose **Command Prompt** from the terminal dropdown for the commands below.

## 2. Set up Python 3.11

Check whether Python 3.11 is installed:

```bat
py -3.11 --version
```

If it is not installed, use the official [Python Windows downloads](https://www.python.org/downloads/windows/) or Python install manager to install Python 3.11, then reopen VS Code. Avoid third-party installers. Use 64-bit Python.

Create an isolated environment:

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

The version should begin with **3.11**. The first install is large because the app includes CPU machine-learning libraries. Keep both requirements files together; do not replace them with the old two-line requirements.

If using PowerShell and activation is blocked, run commands through the environment directly without changing the execution policy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

On macOS/Linux, use `python3.11 -m venv .venv` and `source .venv/bin/activate`.

## 3. Add a free Groq key

The provider is **Groq**, not xAI's **Grok**.

1. Open [Groq API keys](https://console.groq.com/keys).
2. Create a free account/key if needed.
3. In `.streamlit`, copy `secrets.toml.example` to a new file named `secrets.toml`.
4. Edit only the new file:

```toml
GROQ_API_KEY = "paste-your-real-key-here"
GROQ_MODEL = "openai/gpt-oss-120b"
```

Do not post the real key in GitHub, screenshots or public messages. The included `.gitignore` excludes `.streamlit/secrets.toml`.

## 4. Run and test locally

```bat
python -m streamlit run app.py
```

Open the local address printed in the terminal. Try:

1. **Quantity takeoff** -> **Plaster** -> **Calculate & save takeoff**.
2. **Knowledge base** -> **Use demo specification**. First use downloads the embedding model; no Hugging Face token is required for this public model.
3. Search `What plaster thickness is specified?`.
4. **CiviGuide AI** -> **Documents only** -> ask the same question.
5. **Agent review** -> **Single agent** -> compare the saved thickness against the specification.
6. **Project & exports** -> download the JSON and PDF.

Optional tests, in another activated terminal:

```bat
python -m unittest discover -s tests -v
python scripts/check_live_ai.py
```

The first command uses scripted AI responses and no Groq key. The second uses your real free-tier quota. AI usage is limited by your Groq organization, shared by all people using the same key.

## 5. Create your GitHub repository

Install [Git](https://git-scm.com/downloads) if `git --version` is not recognized. Restart the terminal after installing.

1. Sign in to [GitHub](https://github.com/).
2. Click **+ -> New repository**.
3. Name it `civil-quantestimate-v2`.
4. Choose Public if you intend to share the source; choose Private if you want to restrict source access.
5. For these commands, leave **Add README**, **Add .gitignore** and **Choose a license** unselected. Those first two files already exist locally; choose a code licence separately when you decide how others may use your work.
6. Click **Create repository**.
7. Copy the repository HTTPS URL shown by GitHub.

In your project terminal:

```bat
git init
git branch -M main
git add .
git status
```

Before committing, check that `.streamlit/secrets.toml` and `.venv` are absent from the staged files. You can verify the ignore rule with:

```bat
git check-ignore .streamlit/secrets.toml
```

Commit and upload:

```bat
git commit -m "Build Civil QuantEstimate v2 with RAG and CrewAI"
git remote add origin https://github.com/YOUR_USERNAME/civil-quantestimate-v2.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username. If Git asks for your name/email, use your own values with `git config user.name "Your Name"` and `git config user.email "your-email"`, then retry the commit. Complete GitHub authentication using the browser prompt or an appropriate token; a GitHub account password is not accepted for HTTPS Git authentication.

Refresh the GitHub repository and check that `app.py` is at the repository root. Uploading only the ZIP will not deploy the app: the extracted files must be committed.

## 6. Deploy on Streamlit Community Cloud

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and connect your GitHub account.
2. Select **Create app**, then **Yup, I have an app** if shown.
3. Select your repository and set:

| Setting | Value |
| --- | --- |
| Repository | `YOUR_USERNAME/civil-quantestimate-v2` |
| Branch | `main` |
| Main file path | `app.py` |
| Python version | **3.11**, under **Advanced settings** |

4. In **Advanced settings -> Secrets**, paste:

```toml
GROQ_API_KEY = "your-real-key"
GROQ_MODEL = "openai/gpt-oss-120b"
```

5. Save the settings and click **Deploy**.
6. Check the build logs. The dependency installation and first model download can take several minutes.
7. Repeat the six local checks above on the deployed app. Also test it on your phone.

Select Python in the deployment UI. `.python-version` documents the local target; it is not a substitute for the Community Cloud Python selector. If 3.11 is no longer offered, do not silently change versions: this package's Linux CPU wheel targets 3.11 and needs an updated dependency set for another version.

The app uses a CPU-only PyTorch wheel on Linux x86_64 to avoid unnecessary CUDA downloads. Keep `constraints.txt` in the repository. Do not add a second dependency manager file such as `uv.lock`, `Pipfile` or `environment.yml` unless you intentionally switch the deployment installation method.

## 7. Publish later updates

After changing files and checking the app locally:

```bat
git add .
git status
git commit -m "Describe your change"
git push
```

Community Cloud picks up repository changes. Update keys using Streamlit's Secrets settings, never through a code commit.

## If something fails

| Symptom | First action |
| --- | --- |
| Python or dependency conflict | Confirm Python 3.11 and use a new virtual environment with both supplied requirements files |
| `ModuleNotFoundError` | Run with the same environment used to install requirements; do not run only `app.py` directly |
| Groq 401/403 | Check the key, model permissions and Secrets settings |
| Groq 429 | Wait and inspect your Groq usage limits; use single-agent mode and shorter questions |
| Embedding model cannot load | Check internet access and memory; try the small demo document first |
| PDF has no readable text | OCR it with a suitable tool before uploading, or use TXT/MD |
| Wrong document answer | Inspect the displayed passages; upload clearer text and ask a more specific question |
| Cloud app runs out of memory | Use smaller document sets and fewer simultaneous sessions; free-host memory is limited |
| Work disappeared after restart | Import your exported JSON and rebuild the document index |

This is a working hackathon foundation, not a guarantee of error-free engineering decisions or unlimited free hosting. The package includes a record of completed checks in `docs/VALIDATION.md`.
