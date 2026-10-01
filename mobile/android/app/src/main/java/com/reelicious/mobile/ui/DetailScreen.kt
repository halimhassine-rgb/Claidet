package com.reelicious.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.StarBorder
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.reelicious.mobile.data.Recipe

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailScreen(
    recipeId: String,
    viewModel: AppViewModel,
    onEdit: (Recipe) -> Unit,
    onDeleted: () -> Unit,
    onBack: () -> Unit,
) {
    var recipe by remember { mutableStateOf<Recipe?>(null) }
    var showDeleteConfirm by remember { mutableStateOf(false) }
    val recipes by viewModel.recipes.collectAsState()

    LaunchedEffect(recipeId, recipes) {
        recipe = recipes.find { it.id == recipeId } ?: viewModel.getRecipe(recipeId)
    }

    val current = recipe
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(current?.title ?: "Recette") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Retour")
                    }
                },
                actions = {
                    if (current != null) {
                        IconButton(onClick = {
                            viewModel.editRecipe(current)
                            onEdit(current)
                        }) {
                            Icon(Icons.Default.Edit, contentDescription = "Modifier")
                        }
                        IconButton(onClick = { showDeleteConfirm = true }) {
                            Icon(Icons.Default.Delete, contentDescription = "Supprimer")
                        }
                    }
                },
            )
        },
    ) { padding ->
        if (current == null) {
            Box(Modifier.fillMaxSize().padding(padding))
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item { CoverThumbnail(path = current.coverImagePath, size = 160.dp) }
                item {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { viewModel.toggleFavorite(current.id, !current.isFavorite) }) {
                            Icon(
                                if (current.isFavorite) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                                contentDescription = "Favori",
                                tint = MaterialTheme.colorScheme.primary,
                            )
                        }
                        RatingStars(rating = current.rating, onRate = { viewModel.setRating(current.id, it) })
                    }
                }
                current.category?.let { category ->
                    item { AssistChip(onClick = {}, label = { Text(category) }) }
                }
                current.servings?.let { servings ->
                    item { Text("Portions : $servings") }
                }
                item { Text("Ingrédients", style = MaterialTheme.typography.titleMedium) }
                items(current.ingredients) { ingredient ->
                    Text("• ${ingredient.quantity?.let { "$it " } ?: ""}${ingredient.name}")
                }
                item { Text("Étapes", style = MaterialTheme.typography.titleMedium) }
                items(current.steps) { step ->
                    Text("${step.order}. ${step.text}")
                }
                current.notes?.takeIf { it.isNotBlank() }?.let { notes ->
                    item { Text("Notes", style = MaterialTheme.typography.titleMedium) }
                    item { Text(notes) }
                }
            }
        }
    }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text("Supprimer cette recette ?") },
            text = { Text("Cette action est définitive.") },
            confirmButton = {
                TextButton(onClick = {
                    showDeleteConfirm = false
                    viewModel.deleteRecipe(recipeId, onDeleted = onDeleted)
                }) { Text("Supprimer") }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) { Text("Annuler") }
            },
        )
    }
}

@Composable
private fun RatingStars(rating: Int?, onRate: (Int?) -> Unit) {
    Row {
        for (i in 1..5) {
            val filled = (rating ?: 0) >= i * 2
            IconButton(onClick = { onRate(if (rating == i * 2) null else i * 2) }, modifier = Modifier.size(32.dp)) {
                Icon(
                    if (filled) Icons.Default.Star else Icons.Default.StarBorder,
                    contentDescription = "Note",
                    tint = MaterialTheme.colorScheme.secondary,
                )
            }
        }
    }
}
