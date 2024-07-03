module.exports = {
  testMatch: [ '<rootDir>/tests/integ/**/*.test.ts'],
  transform: {
    "^.+\\.tsx?$": "ts-jest"
  },
  reporters: [
    "default",
    ["jest-junit", {outputDirectory: "../reports/", outputName: `payment-3p-integ.xml`}]
  ],
}
