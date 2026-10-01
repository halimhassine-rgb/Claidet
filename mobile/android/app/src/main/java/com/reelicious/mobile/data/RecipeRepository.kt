package com.reelicious.mobile.data

import android.content.Context
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.io.File
import java.util.UUID

/**
 * Équivalent mobile de `storage.repository.RecipeRepository` : même rôle
 * (seul point d'entrée pour lire/écrire des recettes, gère la copie de
 * l'image de couverture dans un répertoire durable), en nettement plus
 * simple puisque Room gère déjà le fichier SQLite.
 */
class RecipeRepository(context: Context) {
    private val dao = AppDatabase.get(context).recipeDao()
    private val coversDir = File(context.filesDir, "covers").apply { mkdirs() }

    val recipes: Flow<List<Recipe>> =
        dao.observeAll().map { entities -> entities.map { it.toDomain() } }

    suspend fun get(id: String): Recipe? = dao.getById(id)?.toDomain()

    suspend fun findBySourceUrl(url: String): Recipe? = dao.findBySourceUrl(url)?.toDomain()

    suspend fun listCategories(): List<String> = dao.listCategories()

    /** Enregistre (création ou mise à jour). Copie l'image de couverture
     * dans le répertoire durable si elle vient d'un fichier temporaire
     * (ex. une image clé extraite pendant le pipeline, qui sera
     * supprimée ensuite). */
    suspend fun save(recipe: Recipe): Recipe {
        val existing = dao.getById(recipe.id)?.toDomain()
        val persistedCover = persistCoverImage(recipe.coverImagePath, existing?.coverImagePath)

        val toSave = recipe.copy(
            coverImagePath = persistedCover,
            sortOrder = existing?.sortOrder ?: dao.nextSortOrder(),
            createdAt = existing?.createdAt ?: recipe.createdAt,
            updatedAt = System.currentTimeMillis(),
        )
        dao.upsert(toSave.toEntity())
        return toSave
    }

    suspend fun delete(id: String) {
        val recipe = dao.getById(id)?.toDomain()
        dao.deleteById(id)
        recipe?.coverImagePath?.let { path ->
            runCatching { File(path).delete() }
        }
    }

    suspend fun setFavorite(id: String, value: Boolean) {
        val recipe = dao.getById(id)?.toDomain() ?: return
        dao.upsert(recipe.copy(isFavorite = value, updatedAt = System.currentTimeMillis()).toEntity())
    }

    suspend fun setRating(id: String, value: Int?) {
        val recipe = dao.getById(id)?.toDomain() ?: return
        dao.upsert(recipe.copy(rating = value, updatedAt = System.currentTimeMillis()).toEntity())
    }

    private fun persistCoverImage(newPath: String?, previousPersistedPath: String?): String? {
        if (newPath == null) return previousPersistedPath
        val newFile = File(newPath)
        if (!newFile.exists()) return previousPersistedPath
        // Déjà dans le répertoire durable (ex. re-sauvegarde sans changer
        // l'image) : rien à faire.
        if (newFile.parentFile == coversDir) return newPath

        val dest = File(coversDir, "${UUID.randomUUID()}_${newFile.name}")
        newFile.copyTo(dest, overwrite = true)
        if (previousPersistedPath != null && previousPersistedPath != dest.path) {
            runCatching { File(previousPersistedPath).delete() }
        }
        return dest.path
    }
}
