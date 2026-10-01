package com.reelicious.mobile.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Équivalent mobile de ANTHROPIC_API_KEY dans ~/.reelicious/.env côté
 * bureau : il n'y a pas de fichier .env sur téléphone, la clé est saisie
 * une fois dans l'appli (écran Réglages) et stockée chiffrée localement.
 */
class ApiKeyStore(context: Context) {
    private val prefs = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "reelicious_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun getApiKey(): String? = prefs.getString(KEY_API_KEY, null)?.takeIf { it.isNotBlank() }

    fun setApiKey(value: String) {
        prefs.edit().putString(KEY_API_KEY, value.trim()).apply()
    }

    fun clear() {
        prefs.edit().remove(KEY_API_KEY).apply()
    }

    companion object {
        private const val KEY_API_KEY = "anthropic_api_key"
    }
}
