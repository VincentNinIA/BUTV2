@echo off
REM Script de lancement pour RAG-NINIA sur Windows
REM Utilise automatiquement l'environnement virtuel correct

echo 🦋 RAG-NINIA - Lancement de l'application
echo =================================================

REM Vérifier si l'environnement virtuel existe
if not exist "venv" (
    echo ❌ Environnement virtuel non trouvé !
    echo Veuillez d'abord installer l'environnement avec :
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Vérifier si le fichier .env existe
if not exist ".env" (
    echo ⚠️  Fichier .env manquant !
    echo Copie du template .env...
    if exist ".env.template" (
        copy .env.template .env
        echo ✅ Fichier .env créé à partir du template
        echo ⚠️  N'oubliez pas de configurer vos clés API dans le fichier .env
    ) else (
        echo ❌ Template .env.template non trouvé !
        echo Veuillez créer un fichier .env avec vos clés API
        pause
        exit /b 1
    )
)

REM Vérifier les clés API
echo 🔍 Vérification de la configuration...
findstr /C:"votre_cle_openai_ici" .env >nul
if %errorlevel% equ 0 (
    echo ⚠️  La clé OpenAI n'est pas configurée !
    echo Veuillez modifier le fichier .env et remplacer 'votre_cle_openai_ici' par votre vraie clé OpenAI
    pause
    exit /b 1
)

findstr /C:"votre_cle_pinecone_ici" .env >nul
if %errorlevel% equ 0 (
    echo ⚠️  La clé Pinecone n'est pas configurée !
    echo Veuillez modifier le fichier .env et remplacer 'votre_cle_pinecone_ici' par votre vraie clé Pinecone
    pause
    exit /b 1
)

echo ✅ Configuration OK

REM Lancer l'application avec le bon environnement virtuel
echo 🚀 Lancement de l'application...
echo L'application va s'ouvrir dans votre navigateur à l'adresse : http://localhost:8501
echo.
echo 💡 Pour arrêter l'application, appuyez sur Ctrl+C
echo.

REM Utiliser directement le python de l'environnement virtuel
venv\Scripts\python.exe -m streamlit run app_streamlit\chatbot_ninia.py 