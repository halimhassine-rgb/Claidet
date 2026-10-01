package com.reelicious.mobile.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.reelicious.mobile.data.ApiKeyStore
import com.reelicious.mobile.data.Recipe
import com.reelicious.mobile.data.RecipeRepository
import com.reelicious.mobile.network.RecipeReconstructionException
import com.reelicious.mobile.pipeline.ExtractionException
import com.reelicious.mobile.pipeline.ExtractionPipeline
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

sealed class ExtractionUiState {
    data object Idle : ExtractionUiState()
    data object Loading : ExtractionUiState()
    data class Error(val message: String) : ExtractionUiState()
}

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = RecipeRepository(application)
    private val apiKeyStore = ApiKeyStore(application)
    private val pipeline = ExtractionPipeline(application)

    val recipes: StateFlow<List<Recipe>> = repository.recipes
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _extractionState = MutableStateFlow<ExtractionUiState>(ExtractionUiState.Idle)
    val extractionState: StateFlow<ExtractionUiState> = _extractionState.asStateFlow()

    private val _pendingReview = MutableStateFlow<Recipe?>(null)
    val pendingReview: StateFlow<Recipe?> = _pendingReview.asStateFlow()

    fun getApiKey(): String? = apiKeyStore.getApiKey()
    fun setApiKey(value: String) = apiKeyStore.setApiKey(value)

    fun startExtraction(url: String, onReady: () -> Unit) {
        val apiKey = apiKeyStore.getApiKey()
        if (apiKey == null) {
            _extractionState.value = ExtractionUiState.Error(
                "Aucune clé API configurée. Va dans Réglages pour la renseigner.",
            )
            return
        }
        _extractionState.value = ExtractionUiState.Loading
        viewModelScope.launch {
            try {
                val recipe = pipeline.extract(url.trim(), apiKey)
                _pendingReview.value = recipe
                _extractionState.value = ExtractionUiState.Idle
                onReady()
            } catch (exc: ExtractionException) {
                _extractionState.value = ExtractionUiState.Error(exc.message ?: "Échec de l'extraction.")
            } catch (exc: RecipeReconstructionException) {
                _extractionState.value = ExtractionUiState.Error(exc.message ?: "Échec de la reconstruction.")
            } catch (exc: Exception) {
                _extractionState.value = ExtractionUiState.Error("Erreur inattendue : ${exc.message}")
            }
        }
    }

    fun startManualEntry() {
        _pendingReview.value = Recipe(title = "", extractionMethod = "manual")
    }

    fun editRecipe(recipe: Recipe) {
        _pendingReview.value = recipe
    }

    fun clearPendingReview() {
        _pendingReview.value = null
    }

    suspend fun getRecipe(id: String): Recipe? = repository.get(id)

    fun saveRecipe(recipe: Recipe, onSaved: (Recipe) -> Unit) {
        viewModelScope.launch {
            val saved = repository.save(recipe)
            onSaved(saved)
        }
    }

    fun deleteRecipe(id: String, onDeleted: () -> Unit) {
        viewModelScope.launch {
            repository.delete(id)
            onDeleted()
        }
    }

    fun toggleFavorite(id: String, value: Boolean) {
        viewModelScope.launch { repository.setFavorite(id, value) }
    }

    fun setRating(id: String, value: Int?) {
        viewModelScope.launch { repository.setRating(id, value) }
    }
}
