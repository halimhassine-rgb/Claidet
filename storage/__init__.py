"""Persistance locale des recettes (SQLite).

Comme `engine`, ce package est indépendant de toute UI : il expose
`RecipeRepository`, utilisable tel quel par l'app de bureau et
réutilisable par un futur serveur.
"""

from storage.repository import RecipeRepository

__all__ = ["RecipeRepository"]
