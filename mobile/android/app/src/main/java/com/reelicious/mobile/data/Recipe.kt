package com.reelicious.mobile.data

import java.util.UUID

/**
 * Modèle de domaine, volontairement proche de `engine.models.Recipe` côté
 * bureau — même liste de champs côté "V1 mobile" (les calories et la
 * transcription audio sont reportées à une version ultérieure, voir
 * mobile/README.md).
 */
data class Ingredient(
    val name: String,
    val quantity: String? = null,
    val note: String? = null,
)

data class Step(
    val order: Int,
    val text: String,
)

data class Recipe(
    val id: String = UUID.randomUUID().toString(),
    val sourceUrl: String? = null,
    val title: String,
    val category: String? = null,
    val servings: String? = null,
    val ingredients: List<Ingredient> = emptyList(),
    val steps: List<Step> = emptyList(),
    val notes: String? = null,
    val coverImagePath: String? = null,
    val extractionMethod: String = "manual",
    val rating: Int? = null,
    val isFavorite: Boolean = false,
    val sortOrder: Int = 0,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
)
