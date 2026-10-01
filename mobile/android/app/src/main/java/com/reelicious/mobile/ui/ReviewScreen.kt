package com.reelicious.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.reelicious.mobile.data.Ingredient
import com.reelicious.mobile.data.Recipe
import com.reelicious.mobile.data.Step

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReviewScreen(viewModel: AppViewModel, onSaved: (Recipe) -> Unit, onCancel: () -> Unit) {
    val pending by viewModel.pendingReview.collectAsState()
    val base = pending ?: Recipe(title = "")

    var title by remember(base.id) { mutableStateOf(base.title) }
    var category by remember(base.id) { mutableStateOf(base.category.orEmpty()) }
    var servings by remember(base.id) { mutableStateOf(base.servings.orEmpty()) }
    var notes by remember(base.id) { mutableStateOf(base.notes.orEmpty()) }
    val ingredients = remember(base.id) { mutableStateListOf(*base.ingredients.toTypedArray()) }
    val steps = remember(base.id) { mutableStateListOf(*base.steps.toTypedArray()) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Relecture") },
                navigationIcon = {
                    IconButton(onClick = {
                        viewModel.clearPendingReview()
                        onCancel()
                    }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Annuler")
                    }
                },
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item { CoverThumbnail(path = base.coverImagePath, size = 96.dp) }
            item {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Titre") },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item {
                OutlinedTextField(
                    value = category,
                    onValueChange = { category = it },
                    label = { Text("Catégorie") },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item {
                OutlinedTextField(
                    value = servings,
                    onValueChange = { servings = it },
                    label = { Text("Portions") },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item { Text("Ingrédients", style = MaterialTheme.typography.titleMedium) }
            itemsIndexed(ingredients) { index, ingredient ->
                IngredientRow(
                    ingredient = ingredient,
                    onChange = { ingredients[index] = it },
                    onRemove = { ingredients.removeAt(index) },
                )
            }
            item {
                OutlinedButton(onClick = { ingredients.add(Ingredient(name = "")) }, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Ajouter un ingrédient")
                }
            }
            item { Text("Étapes", style = MaterialTheme.typography.titleMedium) }
            itemsIndexed(steps) { index, step ->
                StepRow(
                    step = step,
                    onChange = { steps[index] = it.copy(order = index + 1) },
                    onRemove = { steps.removeAt(index) },
                )
            }
            item {
                OutlinedButton(
                    onClick = { steps.add(Step(order = steps.size + 1, text = "")) },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Ajouter une étape")
                }
            }
            item {
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Notes") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 2,
                )
            }
            item {
                Button(
                    onClick = {
                        val toSave = base.copy(
                            title = title.ifBlank { "Recette sans titre" },
                            category = category.ifBlank { null },
                            servings = servings.ifBlank { null },
                            ingredients = ingredients.toList(),
                            steps = steps.mapIndexed { index, step -> step.copy(order = index + 1) },
                            notes = notes.ifBlank { null },
                        )
                        viewModel.saveRecipe(toSave) { saved ->
                            viewModel.clearPendingReview()
                            onSaved(saved)
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Enregistrer")
                }
            }
        }
    }
}

@Composable
private fun IngredientRow(ingredient: Ingredient, onChange: (Ingredient) -> Unit, onRemove: () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(
            value = ingredient.quantity.orEmpty(),
            onValueChange = { onChange(ingredient.copy(quantity = it.ifBlank { null })) },
            label = { Text("Qté") },
            modifier = Modifier.weight(0.3f),
        )
        OutlinedTextField(
            value = ingredient.name,
            onValueChange = { onChange(ingredient.copy(name = it)) },
            label = { Text("Ingrédient") },
            modifier = Modifier.weight(0.6f),
        )
        IconButton(onClick = onRemove) {
            Icon(Icons.Default.Delete, contentDescription = "Supprimer")
        }
    }
}

@Composable
private fun StepRow(step: Step, onChange: (Step) -> Unit, onRemove: () -> Unit) {
    Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("${step.order}.", modifier = Modifier.padding(top = 16.dp))
        OutlinedTextField(
            value = step.text,
            onValueChange = { onChange(step.copy(text = it)) },
            modifier = Modifier.weight(1f),
            minLines = 1,
        )
        IconButton(onClick = onRemove) {
            Icon(Icons.Default.Delete, contentDescription = "Supprimer")
        }
    }
}
