package com.reelicious.mobile.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface RecipeDao {
    @Query("SELECT * FROM recipes ORDER BY sortOrder ASC")
    fun observeAll(): Flow<List<RecipeEntity>>

    @Query("SELECT * FROM recipes WHERE id = :id")
    suspend fun getById(id: String): RecipeEntity?

    @Query("SELECT * FROM recipes WHERE sourceUrl = :url LIMIT 1")
    suspend fun findBySourceUrl(url: String): RecipeEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(recipe: RecipeEntity)

    @Query("DELETE FROM recipes WHERE id = :id")
    suspend fun deleteById(id: String)

    @Query("SELECT COALESCE(MAX(sortOrder), -1) + 1 FROM recipes")
    suspend fun nextSortOrder(): Int

    @Query("SELECT DISTINCT category FROM recipes WHERE category IS NOT NULL ORDER BY category ASC")
    suspend fun listCategories(): List<String>
}
