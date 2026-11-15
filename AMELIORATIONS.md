# Améliorations de la stratégie : est-ce que ça tient ?

Calculé le 2026-11-15 avec les vrais prix de Kraken, frais de 0,4 % inclus. Toutes les variantes commencent à trader le même jour (après 100 jours d'échauffement), donc les chiffres du bot actuel diffèrent un peu de la comparaison précédente.

## Verdict

Pour chaque variante, sur combien de cryptos elle fait **mieux que le bot actuel**. Une amélioration solide devrait gagner sur 3 ou 4 cryptos dans plusieurs colonnes.

| Variante | Rendement médian (24 réglages) | Chute max plus faible | Médiane sur 6 mois | Pire départ sur 6 mois |
|---|---|---|---|---|
| Stop suiveur 10 % | 0/4 | 0/4 | 1/4 | 3/4 |
| Stop suiveur 15 % | 1/4 | 1/4 | 0/4 | 0/4 |
| Stop suiveur 20 % | 0/4 | 0/4 | 0/4 | 0/4 |
| Filtre de fond 50 j | 3/4 | 3/4 | 1/4 | 3/4 |
| Filtre de fond 100 j | 3/4 | 4/4 | 1/4 | 4/4 |
| Confirmation 2 jours | 1/4 | 4/4 | 3/4 | 3/4 |
| Suiveur 15 % + filtre 100 j | 3/4 | 4/4 | 1/4 | 4/4 |
| Suiveur 15 % + confirmation | 1/4 | 2/4 | 3/4 | 3/4 |
| Filtre 100 j + confirmation | 3/4 | 4/4 | 2/4 | 4/4 |
| Les trois ensemble | 3/4 | 3/4 | 2/4 | 4/4 |

## Rendement avec le réglage du bot

Moyennes 10/30, toute la période. Entre parenthèses : la plus grosse chute temporaire. Acheter et garder : ETH −22 %, BTC −30 %, SOL −52 %, XRP −64 %.

| Variante | ETH | BTC | SOL | XRP |
|---|---|---|---|---|
| **Bot actuel** | +41 % (50 %) | −32 % (44 %) | +30 % (43 %) | −52 % (67 %) |
| Stop suiveur 10 % | −31 % (55 %) | −35 % (46 %) | −33 % (52 %) | −59 % (69 %) |
| Stop suiveur 15 % | −6 % (60 %) | −32 % (44 %) | +41 % (38 %) | −57 % (70 %) |
| Stop suiveur 20 % | +41 % (50 %) | −32 % (44 %) | +27 % (44 %) | −57 % (70 %) |
| Filtre de fond 50 j | +62 % (39 %) | −39 % (49 %) | +20 % (41 %) | −47 % (63 %) |
| Filtre de fond 100 j | +29 % (38 %) | −23 % (36 %) | +18 % (29 %) | −31 % (52 %) |
| Confirmation 2 jours | +39 % (41 %) | −21 % (33 %) | +36 % (38 %) | −51 % (66 %) |
| Suiveur 15 % + filtre 100 j | −14 % (49 %) | −23 % (36 %) | +32 % (25 %) | −36 % (56 %) |
| Suiveur 15 % + confirmation | −8 % (52 %) | −21 % (33 %) | +49 % (33 %) | −56 % (69 %) |
| Filtre 100 j + confirmation | +6 % (43 %) | −14 % (28 %) | +13 % (29 %) | −35 % (55 %) |
| Les trois ensemble | −29 % (54 %) | −14 % (28 %) | +25 % (26 %) | −40 % (59 %) |

## Rendement médian sur 24 réglages de moyennes

Le chiffre le plus fiable : il ne dépend pas d'un réglage précis. Entre parenthèses : nombre de réglages gagnants sur 24.

| Variante | ETH | BTC | SOL | XRP |
|---|---|---|---|---|
| **Bot actuel** | +51 % (23/24) | −15 % (1/24) | −6 % (7/24) | −52 % (0/24) |
| Stop suiveur 10 % | −15 % (5/24) | −28 % (0/24) | −47 % (0/24) | −55 % (0/24) |
| Stop suiveur 15 % | +9 % (14/24) | −18 % (1/24) | −1 % (10/24) | −60 % (0/24) |
| Stop suiveur 20 % | +51 % (23/24) | −15 % (1/24) | −7 % (6/24) | −60 % (0/24) |
| Filtre de fond 50 j | +63 % (24/24) | −16 % (2/24) | −2 % (9/24) | −48 % (0/24) |
| Filtre de fond 100 j | +33 % (23/24) | −2 % (9/24) | +4 % (14/24) | −33 % (0/24) |
| Confirmation 2 jours | +33 % (23/24) | −21 % (1/24) | −9 % (7/24) | −46 % (0/24) |
| Suiveur 15 % + filtre 100 j | −13 % (3/24) | −1 % (9/24) | +12 % (19/24) | −41 % (0/24) |
| Suiveur 15 % + confirmation | −8 % (11/24) | −22 % (1/24) | −1 % (10/24) | −52 % (0/24) |
| Filtre 100 j + confirmation | +28 % (22/24) | −7 % (5/24) | +0 % (12/24) | −26 % (0/24) |
| Les trois ensemble | −15 % (2/24) | −7 % (2/24) | +4 % (15/24) | −33 % (0/24) |

## Six mois de bot selon la date de départ

Résultat médian après 6 mois, puis le pire départ. Entre parenthèses : départs gagnants.

| Variante | ETH | BTC | SOL | XRP |
|---|---|---|---|---|
| **Bot actuel** | +10 % / −41 % (9/15) | −13 % / −27 % (2/15) | +6 % / −32 % (8/15) | −29 % / −39 % (5/15) |
| Stop suiveur 10 % | −4 % / −39 % (4/15) | −13 % / −28 % (2/15) | −17 % / −28 % (2/15) | −29 % / −38 % (5/15) |
| Stop suiveur 15 % | −14 % / −41 % (6/15) | −13 % / −27 % (2/15) | +5 % / −33 % (9/15) | −29 % / −39 % (5/15) |
| Stop suiveur 20 % | +10 % / −41 % (9/15) | −13 % / −27 % (2/15) | +6 % / −32 % (8/15) | −29 % / −39 % (5/15) |
| Filtre de fond 50 j | +5 % / −24 % (9/15) | −16 % / −31 % (2/15) | +3 % / −28 % (8/15) | −25 % / −37 % (5/15) |
| Filtre de fond 100 j | −7 % / −18 % (7/15) | −13 % / −20 % (6/15) | +3 % / −17 % (8/15) | −9 % / −26 % (5/15) |
| Confirmation 2 jours | +5 % / −33 % (9/15) | −4 % / −24 % (4/15) | +10 % / −27 % (8/15) | −22 % / −40 % (5/15) |
| Suiveur 15 % + filtre 100 j | −9 % / −18 % (4/15) | −13 % / −20 % (6/15) | +4 % / −17 % (8/15) | −9 % / −25 % (4/15) |
| Suiveur 15 % + confirmation | −13 % / −33 % (6/15) | −4 % / −24 % (4/15) | +9 % / −27 % (9/15) | −22 % / −39 % (5/15) |
| Filtre 100 j + confirmation | −9 % / −20 % (5/15) | −2 % / −20 % (7/15) | +0 % / −17 % (8/15) | −7 % / −38 % (5/15) |
| Les trois ensemble | −10 % / −20 % (1/15) | −2 % / −20 % (7/15) | +2 % / −17 % (8/15) | −7 % / −38 % (4/15) |

## Nombre de transactions

Allers-retours avec le réglage du bot (gagnants entre parenthèses). Plus de transactions = plus de frais.

| Variante | ETH | BTC | SOL | XRP |
|---|---|---|---|---|
| **Bot actuel** | 15 (6) | 13 (3) | 12 (6) | 17 (2) |
| Stop suiveur 10 % | 27 (7) | 15 (4) | 30 (14) | 26 (4) |
| Stop suiveur 15 % | 19 (6) | 13 (3) | 15 (8) | 20 (2) |
| Stop suiveur 20 % | 15 (6) | 13 (3) | 14 (8) | 19 (3) |
| Filtre de fond 50 j | 10 (5) | 13 (3) | 10 (4) | 14 (1) |
| Filtre de fond 100 j | 9 (3) | 10 (3) | 7 (3) | 10 (1) |
| Confirmation 2 jours | 15 (7) | 12 (4) | 11 (6) | 16 (1) |
| Suiveur 15 % + filtre 100 j | 12 (3) | 10 (3) | 10 (5) | 12 (1) |
| Suiveur 15 % + confirmation | 19 (7) | 12 (4) | 14 (8) | 19 (2) |
| Filtre 100 j + confirmation | 10 (3) | 9 (4) | 7 (3) | 10 (1) |
| Les trois ensemble | 13 (3) | 9 (4) | 10 (5) | 12 (1) |

Un bon résultat passé ne garantit rien pour la suite. Ce n'est pas un conseil financier.
