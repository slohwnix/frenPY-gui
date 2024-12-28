import os
import subprocess
import json

def download_file(url, local_path):
    try:
        subprocess.run(["curl", "-k", "-o", local_path, url], check=True)
        print(f"Fichier téléchargé : {local_path}")
    except subprocess.SubprocessError as e:
        print(f"Erreur lors du téléchargement avec curl : {e}")
        exit(1)

def read_json_file(filepath):
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Erreur lors de la lecture du fichier JSON {filepath} : {e}")
        exit(1)

def update_if_needed(local_version, remote_version, local_file_path, json_remote, remote_file_path):
    if local_version < remote_version:
        print("Une mise à jour est nécessaire. Exécution du script de mise à jour...")
        try:
            subprocess.run(["curl", "--ssl-no-revoke", "https://raw.githubusercontent.com/slohwnix/frenPY-ide/refs/heads/main/scripts/frenpy_ide.py", "-o", "scripts/frenpy_ide.py"], check=True)
            print("Script mis à jour avec succès.")
            # Mettre à jour la version dans le fichier local
            with open(local_file_path, 'w') as file:
                json.dump(json_remote, file, indent=4)
            print(f"Version mise à jour dans {local_file_path}")
        except subprocess.SubprocessError as e:
            print(f"Erreur lors de la mise à jour du script : {e}")
            exit(1)
    else:
        print("Aucune mise à jour nécessaire.")
    # Supprimer le fichier distant après la mise à jour
    os.remove(remote_file_path)
    print(f"Fichier supprimé : {remote_file_path}")

def install_dependencies():
    try:
        subprocess.run(["python", "-m", "pip", "install", "pyqt6", "frenpy", "--upgrade"], check=True)
    except subprocess.SubprocessError as e:
        print(f"Erreur lors de l'installation des dépendances : {e}")
        exit(1)

def run_python_script(script_path):
    try:
        subprocess.run(["python", script_path], check=True)
    except subprocess.SubprocessError as e:
        print(f"Erreur lors de l'exécution du script Python : {e}")
        exit(1)

def main():
    directory_path = "./data"

    # Vérification de l'existence du répertoire
    if not os.path.exists(directory_path):
        print("Erreur : Le répertoire 'data' est introuvable.")
        exit(1)

    # Télécharger le fichier config_remote.json
    remote_url = "https://raw.githubusercontent.com/slohwnix/frenPY-ide/refs/heads/main/data/config.json"
    remote_file_path = os.path.join(directory_path, "config_remote.json")
    download_file(remote_url, remote_file_path)

    # Lire les fichiers JSON
    local_file_path = os.path.join(directory_path, "config.json")
    json_remote = read_json_file(remote_file_path)
    json_local = read_json_file(local_file_path)

    # Comparer les versions et effectuer les mises à jour si nécessaire
    local_version = json_local.get("version", "0.0.0")
    remote_version = json_remote.get("version", "0.0.0")
    update_if_needed(local_version, remote_version, local_file_path, json_remote, remote_file_path)

    # Installer les dépendances et exécuter le script Python
    install_dependencies()
    

if __name__ == "__main__":
    main()
