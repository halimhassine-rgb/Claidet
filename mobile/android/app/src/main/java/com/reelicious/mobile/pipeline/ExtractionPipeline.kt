package com.reelicious.mobile.pipeline

import android.content.Context
import com.chaquo.python.Python
import com.reelicious.mobile.data.Recipe
import com.reelicious.mobile.util.optStringOrNull
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.util.UUID

class ExtractionException(message: String, cause: Throwable? = null) : Exception(message, cause)

/**
 * Équivalent mobile de `engine.pipeline.ExtractionPipeline` : orchestre
 * téléchargement -> images clés -> reconstruction Claude. Pas d'extraction
 * audio ni de transcription en V1 (voir mobile/README.md) — pas de
 * conservation de la vidéo non plus, contrainte explicite du mobile :
 * seules l'image de couverture et les données texte survivent.
 */
class ExtractionPipeline(private val context: Context) {

    private val maxKeyFrames = 6

    suspend fun extract(url: String, apiKey: String): Recipe = withContext(Dispatchers.IO) {
        val workDir = File(context.cacheDir, "extraction_${UUID.randomUUID()}")
        workDir.mkdirs()
        try {
            val downloaded = downloadVideo(url, workDir)
            val videoFile = File(downloaded.videoPath)

            val frames = try {
                FrameExtractor.extractKeyFrames(videoFile, workDir, maxFrames = maxKeyFrames)
            } catch (exc: FrameExtractionException) {
                emptyList()
            }

            val coverSource = downloaded.thumbnailPath?.let(::File)?.takeIf { it.exists() }
                ?: frames.firstOrNull()

            val recipe = com.reelicious.mobile.network.ClaudeClient(apiKey).reconstruct(
                caption = downloaded.caption,
                framePaths = frames,
                sourceUrl = url,
            )

            recipe.copy(coverImagePath = coverSource?.path)
        } finally {
            // Jamais de vidéo conservée sur le téléphone : tout le
            // répertoire de travail (vidéo téléchargée + images clés
            // temporaires) est supprimé une fois la recette reconstruite.
            // Seule l'image de couverture, copiée par RecipeRepository
            // avant cet appel, survit ailleurs sur le disque.
            workDir.deleteRecursively()
        }
    }

    private fun downloadVideo(url: String, destDir: File): DownloadedVideo {
        val py = Python.getInstance()
        val module = py.getModule("reelicious_download")
        val resultJson = try {
            module.callAttr("download", url, destDir.absolutePath).toString()
        } catch (exc: Exception) {
            throw ExtractionException("Échec du téléchargement : ${exc.message}", exc)
        }

        val obj = JSONObject(resultJson)
        return DownloadedVideo(
            videoPath = obj.optStringOrNull("video_path")
                ?: throw ExtractionException("Téléchargement sans chemin vidéo."),
            caption = obj.optStringOrNull("caption"),
            thumbnailPath = obj.optStringOrNull("thumbnail_path"),
        )
    }

    private data class DownloadedVideo(
        val videoPath: String,
        val caption: String?,
        val thumbnailPath: String?,
    )
}
