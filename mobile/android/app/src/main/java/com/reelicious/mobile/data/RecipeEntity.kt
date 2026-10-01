package com.reelicious.mobile.data

import androidx.room.Entity
import androidx.room.PrimaryKey
import org.json.JSONArray
import org.json.JSONObject

@Entity(tableName = "recipes")
data class RecipeEntity(
    @PrimaryKey val id: String,
    val sourceUrl: String?,
    val title: String,
    val category: String?,
    val servings: String?,
    val ingredientsJson: String,
    val stepsJson: String,
    val notes: String?,
    val coverImagePath: String?,
    val extractionMethod: String,
    val rating: Int?,
    val isFavorite: Boolean,
    val sortOrder: Int,
    val createdAt: Long,
    val updatedAt: Long,
)

fun Recipe.toEntity(): RecipeEntity = RecipeEntity(
    id = id,
    sourceUrl = sourceUrl,
    title = title,
    category = category,
    servings = servings,
    ingredientsJson = ingredientsToJson(ingredients),
    stepsJson = stepsToJson(steps),
    notes = notes,
    coverImagePath = coverImagePath,
    extractionMethod = extractionMethod,
    rating = rating,
    isFavorite = isFavorite,
    sortOrder = sortOrder,
    createdAt = createdAt,
    updatedAt = updatedAt,
)

fun RecipeEntity.toDomain(): Recipe = Recipe(
    id = id,
    sourceUrl = sourceUrl,
    title = title,
    category = category,
    servings = servings,
    ingredients = ingredientsFromJson(ingredientsJson),
    steps = stepsFromJson(stepsJson),
    notes = notes,
    coverImagePath = coverImagePath,
    extractionMethod = extractionMethod,
    rating = rating,
    isFavorite = isFavorite,
    sortOrder = sortOrder,
    createdAt = createdAt,
    updatedAt = updatedAt,
)

private fun ingredientsToJson(ingredients: List<Ingredient>): String {
    val array = JSONArray()
    for (ingredient in ingredients) {
        val obj = JSONObject()
        obj.put("name", ingredient.name)
        obj.put("quantity", ingredient.quantity)
        obj.put("note", ingredient.note)
        array.put(obj)
    }
    return array.toString()
}

private fun ingredientsFromJson(json: String): List<Ingredient> {
    if (json.isBlank()) return emptyList()
    val array = JSONArray(json)
    return (0 until array.length()).map { index ->
        val obj = array.getJSONObject(index)
        Ingredient(
            name = obj.getString("name"),
            quantity = obj.optStringOrNull("quantity"),
            note = obj.optStringOrNull("note"),
        )
    }
}

private fun stepsToJson(steps: List<Step>): String {
    val array = JSONArray()
    for (step in steps) {
        val obj = JSONObject()
        obj.put("order", step.order)
        obj.put("text", step.text)
        array.put(obj)
    }
    return array.toString()
}

private fun stepsFromJson(json: String): List<Step> {
    if (json.isBlank()) return emptyList()
    val array = JSONArray(json)
    return (0 until array.length()).map { index ->
        val obj = array.getJSONObject(index)
        Step(order = obj.getInt("order"), text = obj.getString("text"))
    }
}

private fun JSONObject.optStringOrNull(key: String): String? =
    if (isNull(key) || !has(key)) null else getString(key)
