# Comparaison de la stratégie sur 4 cryptos

Calculé le 2026-11-15 avec les vrais prix de Kraken (bougies d'un jour, environ 2 ans), frais de 0,4 % par transaction inclus. Réglage du bot : moyennes 10/30, stop-loss 8,0 %.

## Résultat sur toute la période

| Crypto | Paire | Période | Bot | Acheter et garder | Chute max du bot | Trades (gagnants) |
|---|---|---|---|---|---|---|
| **ETH** | ETH/CAD | 659 jours | **+40,8 %** | −47,2 % | 50 % | 15 (6) |
| **BTC** | BTC/CAD | 659 jours | **−32,5 %** | −39,4 % | 44 % | 13 (3) |
| **SOL** | SOL/CAD | 658 jours | **+30,3 %** | −71,2 % | 43 % | 12 (6) |
| **XRP** | XRP/CAD | 659 jours | **−51,6 %** | −70,9 % | 67 % | 17 (2) |

## Solidité du résultat

- **Autres réglages** : sur 24 combinaisons de moyennes, combien finissent gagnantes et combien battent « acheter et garder ».
- **6 mois selon la date de départ** : le bot lancé à différentes dates, un mois d'écart chaque fois.

| Crypto | Réglages gagnants | Réglages qui battent « garder » | Départs gagnants après 6 mois | Médiane 6 mois | Pire 6 mois | Départs avec chute ≥ 20 % |
|---|---|---|---|---|---|---|
| **ETH** | 23/24 | 24/24 | 10/16 | +9,5 % | −41,3 % | 8/16 |
| **BTC** | 1/24 | 24/24 | 4/16 | −8,4 % | −24,9 % | 8/16 |
| **SOL** | 7/24 | 24/24 | 9/16 | +24,3 % | −33,1 % | 13/16 |
| **XRP** | 0/24 | 22/24 | 6/16 | −24,6 % | −39,4 % | 15/16 |

## Comment lire ce tableau

- Une crypto se prête bien à la stratégie si le bot fait mieux que « acheter et garder » **et** si ça tient avec d'autres réglages et d'autres dates de départ.
- La « chute max » est la plus grosse baisse temporaire de la valeur du bot. Au-delà de 20 %, le coupe-circuit du bot vendrait tout et s'arrêterait.
- Toutes ces cryptos suivent en partie le Bitcoin : elles ont souvent chuté en même temps.
- Un bon résultat passé ne garantit rien pour la suite. Ce n'est pas un conseil financier.

