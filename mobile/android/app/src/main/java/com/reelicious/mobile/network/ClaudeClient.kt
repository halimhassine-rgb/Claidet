package com.reelicious.mobile.network

import android.util.Base64
import com.reelicious.mobile.data.Ingredient
import com.reelicious.mobile.data.Recipe
import com.reelicious.mobile.data.Step
import com.reelicious.mobile.util.optStringOrNull
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

class RecipeReconstructionException(message: String, cause: Throwable? = null) :
    Exception(message, cause)

/**
 * Appel direct à l'API Claude depuis le téléphone — aucun serveur
 * intermédiaire, exactement comme l'appli de bureau (`engine.recipe_builder
 * .ClaudeRecipeReconstructor`). V1 mobile : pas de transcription audio
 * (voir mobile/README.md), donc seules la légende et les images clés sont
 * envoyées.
 */
class ClaudeClient(private val apiKey: String, private val model: String = "claude-sonnet-5") {

    private val http = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .build()

    suspend fun reconstruct(
        caption: String?,
        framePaths: List<File>,
        sourceUrl: String?,
    ): Recipe = withContext(Dispatchers.IO) {
        val textPart = if (caption.isNullOrBlank()) {
            "(Aucune légende disponible : base-toi uniquement sur les images.)"
        } else {
            "Légende du post :\n$caption"
        }

        val content = JSONArray()
        content.put(JSONObject().put("type", "text").put("text", textPart))
        for (path in framePaths) {
            content.put(encodeImageBlock(path))
        }

        val body = JSONObject().apply {
            put("model", model)
            put("max_tokens", 2000)
            put("system", SYSTEM_PROMPT)
            put(
                "messages",
                JSONArray().put(
                    JSONObject().put("role", "user").put("content", content),
                ),
            )
        }

        val request = Request.Builder()
            .url("https://api.anthropic.com/v1/messages")
            .addHeader("x-api-key", apiKey)
            .addHeader("anthropic-version", "2023-06-01")
            .addHeader("content-type", "application/json")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()

        val responseText = try {
            http.newCall(request).execute().use { response ->
                val bodyText = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    throw RecipeReconstructionException(
                        "Échec de l'appel au modèle (HTTP ${response.code}) : ${bodyText.take(300)}",
                    )
                }
                bodyText
            }
        } catch (exc: RecipeReconstructionException) {
            throw exc
        } catch (exc: Exception) {
            throw RecipeReconstructionException("Échec de l'appel au modèle : ${exc.message}", exc)
        }

        val rawText = extractAssistantText(responseText)
        val payload = extractJson(rawText)
        payloadToRecipe(payload, sourceUrl)
    }

    private fun extractAssistantText(responseJson: String): String {
        val root = JSONObject(responseJson)
        val blocks = root.optJSONArray("content") ?: JSONArray()
        val builder = StringBuilder()
        for (i in 0 until blocks.length()) {
            val block = blocks.getJSONObject(i)
            if (block.optString("type") == "text") {
                builder.append(block.optString("text"))
            }
        }
        return builder.toString()
    }

    private fun extractJson(rawText: String): JSONObject {
        val text = rawText.trim()
        val start = text.indexOf('{')
        val end = text.lastIndexOf('}')
        if (start == -1 || end == -1 || end < start) {
            throw RecipeReconstructionException(
                "Réponse du modèle sans JSON exploitable : ${text.take(200)}",
            )
        }
        return try {
            JSONObject(text.substring(start, end + 1))
        } catch (exc: Exception) {
            throw RecipeReconstructionException("JSON invalide renvoyé par le modèle : ${exc.message}", exc)
        }
    }

    private fun payloadToRecipe(payload: JSONObject, sourceUrl: String?): Recipe {
        val ingredients = payload.optJSONArray("ingredients")?.let { array ->
            (0 until array.length()).map { index ->
                val item = array.getJSONObject(index)
                Ingredient(
                    name = item.optString("name"),
                    quantity = item.optStringOrNull("quantity"),
                    note = item.optStringOrNull("note"),
                )
            }
        } ?: emptyList()

        val steps = payload.optJSONArray("steps")?.let { array ->
            (0 until array.length()).map { index -> array.getString(index) }
                .mapIndexed { index, text -> Step(order = index + 1, text = text) }
        } ?: emptyList()

        val title = payload.optStringOrNull("title")?.takeIf { it.isNotBlank() } ?: "Recette sans titre"

        return Recipe(
            sourceUrl = sourceUrl,
            title = title,
            category = payload.optStringOrNull("category"),
            servings = payload.optStringOrNull("servings"),
            ingredients = ingredients,
            steps = steps,
            notes = payload.optStringOrNull("notes"),
            extractionMethod = "auto",
        )
    }

    private fun encodeImageBlock(path: File): JSONObject {
        val mediaType = when (path.extension.lowercase()) {
            "png" -> "image/png"
            "webp" -> "image/webp"
            else -> "image/jpeg"
        }
        val data = Base64.encodeToString(path.readBytes(), Base64.NO_WRAP)
        return JSONObject().apply {
            put("type", "image")
            put(
                "source",
                JSONObject().apply {
                    put("type", "base64")
                    put("media_type", mediaType)
                    put("data", data)
                },
            )
        }
    }

    companion object {
        private val SUGGESTED_CATEGORIES =
            listOf("Entrée", "Plat", "Dessert", "Apéritif", "Accompagnement", "Boisson")

        private val SYSTEM_PROMPT = """
            Tu extrais une recette de cuisine structurée à partir de deux sources possibles, \
            issues d'un reel Instagram : la légende du post, et des images clés extraites de \
            la vidéo (qui peuvent contenir du texte incrusté : liste d'ingrédients, quantités, \
            étapes). Combine ces sources ; en cas de contradiction, préfère le texte incrusté \
            à l'écran (généralement plus précis) puis la légende.

            Réponds UNIQUEMENT avec un objet JSON, sans texte autour, au format exact :
            {
              "title": string,
              "category": string ou null,
              "servings": string ou null,
              "ingredients": [{"name": string, "quantity": string ou null, "note": string ou null}],
              "steps": [string, ...],
              "notes": string ou null
            }
            Les étapes doivent être dans l'ordre d'exécution, une action par étape.
            Pour "category", choisis de préférence parmi : ${SUGGESTED_CATEGORIES.joinToString(", ")} \
            — ou une autre catégorie courte si aucune ne convient. Ce n'est qu'une suggestion \
            que l'utilisateur pourra corriger, ne force pas une catégorie si le contenu est \
            ambigu : mets null dans ce cas.
            Si une information est réellement absente des sources, mets null plutôt que \
            d'inventer.
        """.trimIndent()
    }
}
