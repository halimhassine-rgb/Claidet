package com.reelicious.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddScreen(
    viewModel: AppViewModel,
    onExtracted: () -> Unit,
    onManualEntry: () -> Unit,
    onBack: () -> Unit,
) {
    var url by remember { mutableStateOf("") }
    val state by viewModel.extractionState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Nouvelle recette") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Retour")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("Colle le lien du reel Instagram à transformer en recette.")
            OutlinedTextField(
                value = url,
                onValueChange = { url = it },
                label = { Text("Lien Instagram") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                enabled = state !is ExtractionUiState.Loading,
            )
            Button(
                onClick = { viewModel.startExtraction(url, onReady = onExtracted) },
                enabled = url.isNotBlank() && state !is ExtractionUiState.Loading,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Extraire la recette")
            }
            OutlinedButton(
                onClick = onManualEntry,
                enabled = state !is ExtractionUiState.Loading,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Saisir une recette à la main")
            }

            when (val s = state) {
                is ExtractionUiState.Loading -> {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        CircularProgressIndicator()
                        Text("Téléchargement et analyse en cours…")
                    }
                }
                is ExtractionUiState.Error -> {
                    Text(s.message, color = MaterialTheme.colorScheme.error)
                }
                else -> {}
            }
        }
    }
}
