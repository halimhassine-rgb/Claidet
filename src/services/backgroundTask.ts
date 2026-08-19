import * as BackgroundTask from 'expo-background-task';
import * as TaskManager from 'expo-task-manager';

import { checkAlertsOnce } from './alertChecker';

export const BACKGROUND_TASK_NAME = 'com.claidet.stockalerts.checkPriceAlerts';

TaskManager.defineTask(BACKGROUND_TASK_NAME, async () => {
  try {
    const { triggered } = await checkAlertsOnce();
    return triggered > 0
      ? BackgroundTask.BackgroundTaskResult.Success
      : BackgroundTask.BackgroundTaskResult.Success;
  } catch {
    return BackgroundTask.BackgroundTaskResult.Failed;
  }
});

export async function registerBackgroundAlertCheck(): Promise<void> {
  const alreadyRegistered = await TaskManager.isTaskRegisteredAsync(BACKGROUND_TASK_NAME);
  if (alreadyRegistered) return;
  await BackgroundTask.registerTaskAsync(BACKGROUND_TASK_NAME, {
    minimumInterval: 15,
  });
}
