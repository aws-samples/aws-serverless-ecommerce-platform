module.exports = {
  collectCoverage: true,
  collectCoverageFrom: [
    "src/**/*.ts",
    "!**/node_modules/**",
    "!**/vendor/**"
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
