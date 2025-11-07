import json
import os
import torch
from tqdm import tqdm

# --- Dependency Imports ---
# Ensure you have installed the required packages:
# pip install torch sentence-transformers langchain langchain-huggingface langchain-community chromadb tqdm huggingface_hub
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain.docstore.document import Document
    from huggingface_hub import snapshot_download
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

def load_all_namc_data():
    """
    Loads and combines concept data from Siddha and Ayurveda JSON files.
    """
    all_concepts = []
    systems_to_load = {
        "Siddha": "Data/SiddhaJson.json",
        "Ayurveda": "Data/AyurvedaJson.json",
    }
    for system_name, file_path in systems_to_load.items():
        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)
                concepts = data.get("concept", [])
                for concept in concepts:
                    concept['system'] = system_name
                all_concepts.extend(concepts)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    return all_concepts

def build_and_save_vector_store():
    """
    Performs the one-time process of building the vector database from source files.
    """
    if not LANGCHAIN_AVAILABLE:
        print("Error: Required packages not found. Please install them first:")
        print("pip install torch sentence-transformers langchain langchain-huggingface langchain-community chromadb tqdm huggingface_hub")
        return

    CHROMA_PERSIST_DIR = "chroma_db_persistent_cli"
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    MODELS_DIR = "models" # Define a dedicated folder for models
    
    if os.path.exists(CHROMA_PERSIST_DIR):
        print(f"Directory '{CHROMA_PERSIST_DIR}' already exists.")
        print("Please remove it if you want to force a rebuild of the model.")
        return

    print("--- Starting Vector Store Preprocessing ---")
    
    # 1. Load NAMC data
    print("Step 1/6: Loading all NAMC data from JSON files...")
    all_namc_concepts = load_all_namc_data()
    if not all_namc_concepts:
        print("Error: No NAMC concepts found in the 'Data' directory. Aborting.")
        return
    print(f"-> Found {len(all_namc_concepts)} concepts.")

    # 2. Prepare documents for LangChain with a progress bar
    print("Step 2/6: Preparing documents for embedding...")
    docs = [
        Document(
            page_content=f"{c.get('display')}: {c.get('designation')[0].get('value')}",
            metadata={
                "code": c.get("code"), "display": c.get("display"),
                "system": c.get("system")
            }
        ) for c in tqdm(all_namc_concepts, desc="Processing concepts") if c.get('designation')
    ]
    print(f"-> Prepared {len(docs)} documents.")

    # 3. Download the model to a specific local folder with a progress bar
    print(f"Step 3/6: Checking for model '{MODEL_NAME}' and downloading to '{MODELS_DIR}' if needed...")
    model_path = os.path.join(MODELS_DIR, MODEL_NAME.replace('/', '_'))
    snapshot_download(
        repo_id=MODEL_NAME,
        local_dir=model_path,
        local_dir_use_symlinks=False # Set to False to copy files for portability
    )
    print(f"-> Model is available locally at '{model_path}'.")

    # 4. Check for PyTorch device (GPU or CPU)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Step 4/6: Detected PyTorch device: '{device}'.")

    # 5. Initialize embedding function from the specific local folder
    print("Step 5/6: Initializing embedding function from local model files...")
    embedding_function = HuggingFaceEmbeddings(
        model_name=model_path, # Use the local path
        model_kwargs={'device': device}
    )
    print("-> Model initialized.")

    # 6. Create and save the vector store
    print(f"Step 6/6: Creating and saving vector store to '{CHROMA_PERSIST_DIR}'...")
    print("(This may take a few minutes...)")
    Chroma.from_documents(
        documents=docs, 
        embedding=embedding_function,
        persist_directory=CHROMA_PERSIST_DIR
    )

    print("\n--- ✅ Preprocessing Complete! ---")
    print(f"The vector store has been successfully saved to the '{CHROMA_PERSIST_DIR}' directory.")
    print(f"Models are stored in the '{MODELS_DIR}' directory.")
    print("You can now use the cli_agent.py for searching.")

if __name__ == "__main__":
    build_and_save_vector_store()

