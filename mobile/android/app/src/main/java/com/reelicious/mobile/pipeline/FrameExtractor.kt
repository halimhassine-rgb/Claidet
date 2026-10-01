package com.reelicious.mobile.pipeline

import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import java.io.File
import java.io.FileOutputStream

class FrameExtractionException(message: String) : Exception(message)

/**
 * Équivalent mobile de `engine.frames.extract_key_frames` : même logique
 * d'échantillonnage (images réparties uniformément, marge de 5 % pour
 * éviter le tout début/la toute fin souvent noirs), mais via l'API Android
 * native `MediaMetadataRetriever` plutôt que ffmpeg — qui n'existe pas en
 * tant que binaire sur Android.
 */
object FrameExtractor {

    fun extractKeyFrames(videoFile: File, destDir: File, maxFrames: Int = 6): List<File> {
        destDir.mkdirs()
        val retriever = MediaMetadataRetriever()
        val framePaths = mutableListOf<File>()
        try {
            retriever.setDataSource(videoFile.absolutePath)
            val durationMs = retriever
                .extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
                ?.toLongOrNull() ?: 0L
            if (durationMs <= 0) {
                throw FrameExtractionException("Durée nulle pour ${videoFile.name}.")
            }

            val durationSec = durationMs / 1000.0
            val count = maxOf(1, maxFrames)
            val margin = durationSec * 0.05
            val span = maxOf(durationSec - 2 * margin, 0.1)
            val timestamps = if (count > 1) {
                (0 until count).map { i -> margin + span * i / (count - 1) }
            } else {
                listOf(durationSec / 2)
            }

            timestamps.forEachIndexed { index, ts ->
                val outFile = File(destDir, "${videoFile.nameWithoutExtension}_frame_${"%02d".format(index)}.jpg")
                // Un timestamp calculé peut tomber après la dernière frame
                // décodable (arrondis de durée) : on retente un peu plus tôt
                // avant d'abandonner cette image, comme côté bureau.
                val saved = listOf(ts, maxOf(ts - 0.5, 0.0)).any { attemptTs ->
                    grabFrame(retriever, attemptTs, outFile)
                }
                if (saved) framePaths.add(outFile)
            }
        } finally {
            retriever.release()
        }

        if (framePaths.isEmpty()) {
            throw FrameExtractionException("Aucune image clé n'a pu être extraite de ${videoFile.name}.")
        }
        return framePaths
    }

    private fun grabFrame(retriever: MediaMetadataRetriever, timestampSec: Double, outFile: File): Boolean {
        val bitmap = try {
            retriever.getFrameAtTime(
                (timestampSec * 1_000_000).toLong(),
                MediaMetadataRetriever.OPTION_CLOSEST,
            )
        } catch (exc: Exception) {
            null
        } ?: return false

        return try {
            FileOutputStream(outFile).use { stream ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 90, stream)
            }
            true
        } catch (exc: Exception) {
            false
        } finally {
            bitmap.recycle()
        }
    }
}
