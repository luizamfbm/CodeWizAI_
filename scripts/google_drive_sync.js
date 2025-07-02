/**
 * This function syncs documents from a source Google Drive folder to a target folder,
 * exporting them as PDFs only if they are new or have been modified.
 * It avoids redundant exports and keeps a lightweight change-tracking cache.
 */
function smartExportToPDF() {
    const SOURCE_FOLDER_ID = '1q8yXnikdF2dfjxt6nHOSDbYPv6nRve_0';   // Folder with original Docs/Sheets/Slides
    const TARGET_FOLDER_ID = '1dnGQdlX7fcQClaBfRqOyPj0zKWuKhhPc';   // Folder to receive exported PDFs
  
    const sourceFolder = DriveApp.getFolderById(SOURCE_FOLDER_ID);
    const targetFolder = DriveApp.getFolderById(TARGET_FOLDER_ID);
    const files = sourceFolder.getFiles();
  
    const cache = PropertiesService.getScriptProperties(); // Stores a map of fileId → lastModified timestamp
    let processedCount = 0;
  
    Logger.log("🔍 Checking for new, modified, or missing exports...");
  
    while (files.hasNext()) {
      const file = files.next();
      const fileId = file.getId();
      const fileName = file.getName();
      const mimeType = file.getMimeType();
      const lastModified = new Date(file.getLastUpdated()).toISOString();
      const cachedTimestamp = cache.getProperty(fileId);
  
      const exportedFileName = fileName + ".pdf";
      const exportedAlready = hasFileInFolder(exportedFileName, targetFolder);
  
      // Skip if file hasn't changed and is already exported
      const shouldSkip = cachedTimestamp === lastModified && exportedAlready;
  
      if (!shouldSkip) {
        try {
          if (
            mimeType === MimeType.GOOGLE_DOCS ||
            mimeType === MimeType.GOOGLE_SHEETS ||
            mimeType === MimeType.GOOGLE_SLIDES
          ) {
            const blob = file.getAs(MimeType.PDF).setName(exportedFileName);
            targetFolder.createFile(blob);
            Logger.log("✅ Exported: " + fileName);
          } else {
            file.makeCopy(fileName, targetFolder); // For non-Google files
            Logger.log("📁 Copied: " + fileName);
          }
  
          cache.setProperty(fileId, lastModified); // Update cache after success
          processedCount++;
        } catch (e) {
          Logger.log(`❌ Error on ${fileName}: ${e.message}`);
        }
      } else {
        Logger.log(`⏩ Skipped (no changes + already exported): ${fileName}`);
      }
    }
  
    Logger.log(`📦 Total processed: ${processedCount}`);
    Logger.log("✅ smartExportToPDF completed.");
  }
  
  /**
   * Utility function that checks if a file with a given name exists in the folder.
   */
  function hasFileInFolder(fileName, folder) {
    const files = folder.getFilesByName(fileName);
    return files.hasNext();
  }
  
  /**
   * This function checks for deleted source documents and removes the corresponding
   * PDF from the target folder to keep things in sync.
   */
  function syncDeletions() {
    const SOURCE_FOLDER_ID = '1q8yXnikdF2dfjxt6nHOSDbYPv6nRve_0';
    const TARGET_FOLDER_ID = '1dnGQdlX7fcQClaBfRqOyPj0zKWuKhhPc';
  
    const sourceFolder = DriveApp.getFolderById(SOURCE_FOLDER_ID);
    const targetFolder = DriveApp.getFolderById(TARGET_FOLDER_ID);
  
    const sourceFileNames = new Set();
  
    // Build a set of all source file names (without .pdf)
    const sourceFiles = sourceFolder.getFiles();
    while (sourceFiles.hasNext()) {
      const file = sourceFiles.next();
      sourceFileNames.add(file.getName());
    }
  
    const targetFiles = targetFolder.getFiles();
    let deletedCount = 0;
  
    Logger.log("🧹 Syncing deletions...");
  
    while (targetFiles.hasNext()) {
      const targetFile = targetFiles.next();
      const targetName = targetFile.getName();
  
      if (targetName.toLowerCase().endsWith(".pdf")) {
        const baseName = targetName.replace(/\.pdf$/i, ""); // Strip ".pdf"
  
        if (!sourceFileNames.has(baseName)) {
          targetFile.setTrashed(true); // Move orphaned PDF to trash
          Logger.log(`🗑️ Deleted orphaned PDF: ${targetName}`);
          deletedCount++;
        }
      }
    }
  
    Logger.log(`✅ Finished syncing deletions. Total deleted: ${deletedCount}`);
  }
  
  /**
   * Master function to run all automation tasks.
   */
  function runAllExports() {
    Logger.log("🚀 Starting full export workflow...");
    smartExportToPDF();
    syncDeletions();
    Logger.log("🏁 All tasks completed.");
  }
  
  /**google apps script: This Apps Script automates the conversion of Drive documents to PDF. You can import this script to Apps Script editor and link it to your Drive folders as shown.”; 
1. Go to [script.google.com](https://script.google.com)  
2.⁠ ⁠Paste the provided ⁠ google-apps-script.js ⁠  
3.⁠ ⁠Update the folder IDs  
4. to run it weekly or daily save the script and set a trigger:
    1. Click on the clock icon in the Apps Script editor
    2. Choose "Time-driven"
    3. Select your preferred frequency (e.g., daily, weekly)
    4. Click *Save* to set the trigger
4.⁠ ⁠Click *Run* to authorize*/