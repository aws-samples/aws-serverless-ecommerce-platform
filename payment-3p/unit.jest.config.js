module.exports = {
  collectCoverage: true,
  collectCoverageFrom: [
    "<rootDir>/build/src/**/*.ts",
    "!**/node_modules/**",
    "!**/vendor/**",
    "!**/*.d.ts"
  ],
  coverageThreshold: {
    "global": {
      "branches": 90,
      "functions": 90,
      "statements": 90
    }
  },
  testMatch: [ '<rootDir>/tests/unit/**/*.test.ts'],
  transform: {
    "^.+\\.tsx?$": "ts-jest"
  },
}
