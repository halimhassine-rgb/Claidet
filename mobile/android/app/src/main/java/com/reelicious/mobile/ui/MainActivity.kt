package com.reelicious.mobile.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.reelicious.mobile.ui.theme.ReeliciousTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ReeliciousTheme {
                val navController = rememberNavController()
                val viewModel: AppViewModel = viewModel()

                NavHost(navController = navController, startDestination = "home") {
                    composable("home") {
                        HomeScreen(
                            viewModel = viewModel,
                            onAddClick = { navController.navigate("add") },
                            onRecipeClick = { id -> navController.navigate("detail/$id") },
                            onSettingsClick = { navController.navigate("settings") },
                        )
                    }
                    composable("add") {
                        AddScreen(
                            viewModel = viewModel,
                            onExtracted = {
                                navController.navigate("review") {
                                    popUpTo("add") { inclusive = true }
                                }
                            },
                            onManualEntry = {
                                viewModel.startManualEntry()
                                navController.navigate("review") {
                                    popUpTo("add") { inclusive = true }
                                }
                            },
                            onBack = { navController.popBackStack() },
                        )
                    }
                    composable("review") {
                        ReviewScreen(
                            viewModel = viewModel,
                            onSaved = { saved ->
                                navController.navigate("detail/${saved.id}") {
                                    popUpTo("home")
                                }
                            },
                            onCancel = { navController.popBackStack("home", inclusive = false) },
                        )
                    }
                    composable(
                        "detail/{recipeId}",
                        arguments = listOf(navArgument("recipeId") { type = NavType.StringType }),
                    ) { backStackEntry ->
                        val recipeId = backStackEntry.arguments?.getString("recipeId")
                        if (recipeId != null) {
                            DetailScreen(
                                recipeId = recipeId,
                                viewModel = viewModel,
                                onEdit = { navController.navigate("review") },
                                onDeleted = { navController.popBackStack("home", inclusive = false) },
                                onBack = { navController.popBackStack() },
                            )
                        }
                    }
                    composable("settings") {
                        SettingsScreen(viewModel = viewModel, onBack = { navController.popBackStack() })
                    }
                }
            }
        }
    }
}
