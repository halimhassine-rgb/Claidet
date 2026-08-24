"""Application de bureau (PySide6).

Seul package du dépôt autorisé à dépendre d'un toolkit UI. Il ne fait
que consommer `engine` (extraction) et `storage` (persistance locale) —
toute la logique métier vit ailleurs, pour rester réutilisable par un
futur client mobile + serveur sans dupliquer quoi que ce soit.
"""
