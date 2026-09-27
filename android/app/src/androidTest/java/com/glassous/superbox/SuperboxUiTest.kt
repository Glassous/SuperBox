package com.glassous.superbox

import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.assertDoesNotExist
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SuperboxUiTest {
    @get:Rule val composeRule = createAndroidComposeRule<MainActivity>()

    @Test fun homeAndThemeMenuAreAvailable() {
        composeRule.onNodeWithText("Superbox").assertExists()
        composeRule.onNodeWithText("全部工具").assertDoesNotExist()
        composeRule.onNodeWithText("搜索工具名称或关键词").assertDoesNotExist()
        composeRule.onNodeWithContentDescription("搜索").performClick()
        composeRule.onNodeWithText("搜索工具名称或关键词").assertExists()
        composeRule.onNodeWithContentDescription("更多选项").performClick()
        composeRule.onNodeWithText("API 接入").assertExists()
        composeRule.onNodeWithText("系统").assertExists()
        composeRule.onNodeWithText("浅色").assertExists()
        composeRule.onNodeWithText("深色").assertExists()
    }
}
