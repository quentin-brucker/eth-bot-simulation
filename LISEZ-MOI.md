# Simulation du bot ETH sur GitHub

Ce dossier contient la version du bot qui tourne toute seule sur GitHub, avec de l'argent fictif.
GitHub réveille le bot toutes les 30 minutes : il regarde le prix, décide, enregistre, puis se rendort.

## Ce qu'il y a dedans

| Fichier | Rôle |
|---|---|
| `bot.py` | Le bot, avec le mode « un seul passage » |
| `dashboard.py` | Met à jour le tableau de bord (la page d'accueil du dépôt) après chaque réveil |
| `config.json` | Les réglages (budget fictif de 200 $) |
| `requirements.txt` | La bibliothèque nécessaire |
| `.github/workflows/simulation.yml` | L'horaire : un réveil toutes les 30 minutes |
| `.gitignore` | Empêche d'envoyer la clé API par erreur |

Il n'y a **aucune clé API** dans ce dépôt, et il ne faut jamais en mettre : la simulation n'en a pas besoin.

## Suivre la simulation

- **Page d'accueil du dépôt** : le tableau de bord (statut, prochain signal, graphiques, transactions). Visible sur github.com ou dans l'app GitHub de ton téléphone.
- `journal.txt` : une ligne à chaque réveil (prix, moyennes, en position ou non, valeur).
- `trades.csv` : chaque achat et chaque vente fictifs.
- `history.csv` : les données des graphiques.
- Onglet **Actions** : la liste des réveils. Une croix rouge veut dire qu'un passage a échoué ; GitHub envoie aussi un courriel.

## Lancer un réveil à la main

Onglet **Actions** > « Simulation bot ETH » > bouton **Run workflow**.

## Arrêter

Onglet **Actions** > « Simulation bot ETH » > bouton « ... » > **Disable workflow**.

## À savoir

- Les réveils de GitHub ont souvent du retard, parfois 10 à 30 minutes, et certains sont sautés. Pour la simulation, ça ne change pas les décisions, qui sont prises une fois par jour.
- Un dépôt privé gratuit a un quota mensuel de minutes. Un réveil toutes les 30 minutes consomme environ 1 440 minutes par mois.
- Cette version sert à la simulation seulement. Le mode réel demande une surveillance plus serrée du stop-loss.
