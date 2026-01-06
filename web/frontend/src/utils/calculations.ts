export const calculateLevelProgress = (level: number, totalXp: number): number => {
  const currentLevelXp = 50 * (level * level) + (100 * level)
  const nextLevelXp = 50 * ((level + 1) * (level + 1)) + (100 * (level + 1))
  const xpInLevel = totalXp - currentLevelXp
  const xpNeeded = nextLevelXp - currentLevelXp
  return Math.min(Math.round((xpInLevel / xpNeeded) * 100), 100)
}

export const calculateXPForLevel = (level: number): number => {
  return 50 * (level * level) + (100 * level)
}

export const calculateLevelFromXP = (xp: number): number => {
  let level = 0
  while (calculateXPForLevel(level + 1) <= xp) {
    level++
  }
  return level
}

export const calculateXPToNextLevel = (currentLevel: number, totalXp: number): number => {
  const nextLevelXp = calculateXPForLevel(currentLevel + 1)
  return Math.max(0, nextLevelXp - totalXp)
}
