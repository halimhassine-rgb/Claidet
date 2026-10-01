package com.reelicious.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.reelicious.mobile.data.Recipe

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    viewModel: AppViewModel,
    onAddClick: () -> Unit,
    onRecipeClick: (String) -> Unit,
    onSettingsClick: () -> Unit,
) {
    val recipes by viewModel.recipes.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Reelicious") },
                actions = {
                    IconButton(onClick = onSettingsClick) {
                        Icon(Icons.Default.Settings, contentDescription = "Réglages")
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = onAddClick) {
                Icon(Icons.Default.Add, contentDescription = "Ajouter une recette")
            }
        },
    ) { padding ->
        if (recipes.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("Aucune recette pour l'instant. Touche + pour en ajouter une.")
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(recipes, key = { it.id }) { recipe ->
                    RecipeRow(
                        recipe = recipe,
                        onClick = { onRecipeClick(recipe.id) },
                        onToggleFavorite = { viewModel.toggleFavorite(recipe.id, !recipe.isFavorite) },
                    )
                }
            }
        }
    }
}

@Composable
private fun RecipeRow(recipe: Recipe, onClick: () -> Unit, onToggleFavorite: () -> Unit) {
    ElevatedCard(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            CoverThumbnail(path = recipe.coverImagePath)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(recipe.title, style = MaterialTheme.typography.titleMedium, maxLines = 2)
                recipe.category?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
                }
            }
            IconButton(onClick = onToggleFavorite) {
                Icon(
                    if (recipe.isFavorite) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                    contentDescription = "Favori",
                    tint = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}
